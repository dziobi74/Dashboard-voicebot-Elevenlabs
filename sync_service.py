"""Service for syncing conversations from ElevenLabs API and computing KPIs."""

import asyncio
import csv
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from database import SessionLocal, Conversation, SyncLog, ArchiveLog, AppSettings
from elevenlabs_client import ElevenLabsClient

logger = logging.getLogger(__name__)

CSV_DIR = os.path.join(os.path.dirname(__file__), "csv_archives")
os.makedirs(CSV_DIR, exist_ok=True)


def get_setting(db: Session, key: str) -> Optional[str]:
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    return row.value if row else None


def set_setting(db: Session, key: str, value: str):
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    if row:
        row.value = value
    else:
        row = AppSettings(key=key, value=value)
        db.add(row)
    db.commit()


def get_agents(db: Session) -> list[dict]:
    """Return configured agents as [{"id": "...", "name": "..."}, ...].

    Handles backward-compatible migration from the old single ``agent_id``
    setting.  If the new ``agents`` key exists it is used; otherwise the
    legacy ``agent_id`` value is wrapped in a single-element list.
    """
    raw = get_setting(db, "agents")
    if raw:
        try:
            agents = json.loads(raw)
            if isinstance(agents, list) and agents:
                return agents
        except (json.JSONDecodeError, TypeError):
            pass

    # Fallback: migrate old single agent_id to new format
    old_id = get_setting(db, "agent_id")
    if old_id:
        return [{"id": old_id, "name": old_id[:12]}]
    return []


def set_agents(db: Session, agents: list[dict]):
    """Persist agents list as JSON in AppSettings."""
    set_setting(db, "agents", json.dumps(agents, ensure_ascii=False))
    # Keep legacy key pointing to first agent for edge-case fallback
    if agents:
        set_setting(db, "agent_id", agents[0]["id"])


async def sync_conversations(
    agent_id: str,
    api_key: str,
    start_unix: Optional[int] = None,
    end_unix: Optional[int] = None,
    sync_type: str = "manual",
    fetch_details: bool = True,
) -> dict:
    """Fetch conversations from ElevenLabs and store in DB. Returns summary."""
    db = SessionLocal()
    log = SyncLog(
        agent_id=agent_id,
        sync_type=sync_type,
        period_from=start_unix,
        period_to=end_unix,
    )
    db.add(log)
    db.commit()

    try:
        client = ElevenLabsClient(api_key)
        conversations = await client.fetch_all_conversations(
            agent_id=agent_id,
            start_after_unix=start_unix,
            start_before_unix=end_unix,
        )
        log.conversations_fetched = len(conversations)

        stored = 0
        for conv in conversations:
            cid = conv.get("conversation_id")
            if not cid:
                continue

            start_ts = conv.get("start_time_unix_secs", 0)
            month_partition = datetime.utcfromtimestamp(start_ts).strftime("%Y-%m") if start_ts else "unknown"

            existing = db.query(Conversation).filter(Conversation.conversation_id == cid).first()
            if existing:
                # Update fields
                existing.status = conv.get("status", existing.status)
                existing.call_successful = conv.get("call_successful", existing.call_successful)
                existing.call_duration_secs = conv.get("call_duration_secs", existing.call_duration_secs)
                existing.message_count = conv.get("message_count", existing.message_count)
                existing.transcript_summary = conv.get("transcript_summary", existing.transcript_summary)
                existing.call_summary_title = conv.get("call_summary_title", existing.call_summary_title)
                existing.main_language = conv.get("main_language", existing.main_language)
                existing.direction = conv.get("direction", existing.direction)
                existing.rating = conv.get("rating", existing.rating)
                existing.tool_names = json.dumps(conv.get("tool_names", []))
            else:
                new_conv = Conversation(
                    conversation_id=cid,
                    agent_id=conv.get("agent_id", agent_id),
                    agent_name=conv.get("agent_name"),
                    status=conv.get("status", "unknown"),
                    call_successful=conv.get("call_successful", "unknown"),
                    start_time_unix=start_ts,
                    call_duration_secs=conv.get("call_duration_secs", 0),
                    message_count=conv.get("message_count", 0),
                    transcript_summary=conv.get("transcript_summary"),
                    call_summary_title=conv.get("call_summary_title"),
                    main_language=conv.get("main_language"),
                    direction=conv.get("direction"),
                    rating=conv.get("rating"),
                    tool_names=json.dumps(conv.get("tool_names", [])),
                    conversation_initiation_source=conv.get("conversation_initiation_source"),
                    month_partition=month_partition,
                )
                db.add(new_conv)
                stored += 1

        db.commit()

        # Fetch details for conversations that don't have them yet
        details_count = 0
        if fetch_details:
            convs_needing_details = (
                db.query(Conversation)
                .filter(
                    Conversation.agent_id == agent_id,
                    Conversation.details_fetched == False,
                )
            )
            if start_unix:
                convs_needing_details = convs_needing_details.filter(Conversation.start_time_unix >= start_unix)
            if end_unix:
                convs_needing_details = convs_needing_details.filter(Conversation.start_time_unix <= end_unix)

            for conv_row in convs_needing_details.all():
                try:
                    detail = await client.get_conversation_detail(conv_row.conversation_id)

                    # Log metadata structure for debugging (first 3 conversations)
                    if details_count < 3:
                        _log_metadata_debug(conv_row.conversation_id, detail)

                    _update_conversation_details(conv_row, detail)

                    # Extra logging: if still no phone after extraction, log warning
                    if not conv_row.agent_phone and not conv_row.client_phone:
                        if details_count < 10:  # log up to 10 missing
                            logger.warning(f"[PHONE MISSING] {conv_row.conversation_id} - no phone found after extraction")
                    details_count += 1
                    if details_count % 10 == 0:
                        db.commit()
                    await asyncio.sleep(0.15)  # rate limit
                except Exception as e:
                    logger.warning(f"Failed to fetch detail for {conv_row.conversation_id}: {e}")

            db.commit()

        log.details_fetched = details_count
        log.status = "completed"
        log.finished_at = datetime.utcnow()
        db.commit()

        return {
            "conversations_fetched": len(conversations),
            "new_stored": stored,
            "details_fetched": details_count,
            "status": "completed",
        }

    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
        log.finished_at = datetime.utcnow()
        db.commit()
        logger.error(f"Sync failed: {e}")
        raise
    finally:
        db.close()


def _log_metadata_debug(conversation_id: str, detail: dict):
    """Log full metadata structure for debugging phone number extraction."""
    meta = detail.get("metadata", {})
    body = meta.get("body", {})
    phone_call = meta.get("phone_call", {})
    client_data = detail.get("conversation_initiation_client_data", {})

    logger.info(f"[DEBUG PHONE] ===== conversation_id={conversation_id} =====")
    logger.info(f"[DEBUG PHONE] metadata keys: {list(meta.keys()) if isinstance(meta, dict) else type(meta)}")

    # Log FULL metadata.body
    if body:
        logger.info(f"[DEBUG PHONE] metadata.body FULL: {json.dumps(body, default=str, ensure_ascii=False)[:2000]}")
    else:
        logger.info(f"[DEBUG PHONE] metadata.body is EMPTY or missing")

    # Log phone_call
    if phone_call:
        logger.info(f"[DEBUG PHONE] metadata.phone_call FULL: {json.dumps(phone_call, default=str, ensure_ascii=False)[:1000]}")
    else:
        logger.info(f"[DEBUG PHONE] metadata.phone_call is EMPTY or missing")

    # Log client_data
    if client_data:
        logger.info(f"[DEBUG PHONE] conversation_initiation_client_data FULL: {json.dumps(client_data, default=str, ensure_ascii=False)[:1000]}")
    else:
        logger.info(f"[DEBUG PHONE] conversation_initiation_client_data is EMPTY or missing")

    # Deep search for phone numbers
    phone_values = _deep_find_phone_values(detail)
    if phone_values:
        logger.info(f"[DEBUG PHONE] Deep search found {len(phone_values)} phone-like values:")
        for path, value in phone_values[:20]:
            logger.info(f"[DEBUG PHONE]   {path} = {value}")
    else:
        logger.info(f"[DEBUG PHONE] Deep search found NO phone-like values in entire response")

    # Log ALL top-level detail keys
    logger.info(f"[DEBUG PHONE] detail top-level keys: {list(detail.keys()) if isinstance(detail, dict) else type(detail)}")

    # Log any nested dicts in metadata we might have missed
    if isinstance(meta, dict):
        for k, v in meta.items():
            if k not in ("body", "phone_call") and isinstance(v, dict):
                logger.info(f"[DEBUG PHONE] metadata.{k} (dict): {json.dumps(v, default=str, ensure_ascii=False)[:500]}")
            elif k not in ("body", "phone_call", "termination_reason", "cost",
                          "call_duration_secs", "start_time_unix_secs"):
                logger.info(f"[DEBUG PHONE] metadata.{k} = {str(v)[:200]}")


def _deep_find_phone_values(obj, path=""):
    """
    Recursively search entire JSON for phone-number-like values.
    Returns list of (path, value) tuples.
    """
    import re
    phone_re = re.compile(r'^\+?\d[\d\s\-]{6,15}\d$')
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            results.extend(_deep_find_phone_values(v, new_path))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            results.extend(_deep_find_phone_values(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        stripped = obj.strip()
        if phone_re.match(stripped):
            results.append((path, stripped))
    return results


def _extract_phone_numbers(detail: dict, meta: dict) -> tuple:
    """
    Extract (agent_phone, client_phone) from conversation detail.

    Tries multiple locations depending on provider:
      1. Twilio:        metadata.body.To / metadata.body.From
      2. SIP Trunking:  metadata.body.to_number / metadata.body.from_number
      3. phone_call:    metadata.phone_call.agent_number / external_number
      4. conversation_initiation_client_data.dynamic_variables
      5. Deep recursive search in entire metadata for phone-related keys
      6. Deep recursive search for any phone-like value patterns
    """
    agent_phone = None
    client_phone = None

    # --- Source 1 & 2: metadata.body (Twilio / SIP) ---
    body = meta.get("body", {})
    if body and isinstance(body, dict):
        # Twilio: "To" = voicebot, "From" = klient
        if body.get("To"):
            agent_phone = body["To"]
        if body.get("From"):
            client_phone = body["From"]

        # SIP Trunking: "to_number" = voicebot, "from_number" = klient
        if not agent_phone and body.get("to_number"):
            agent_phone = body["to_number"]
        if not client_phone and body.get("from_number"):
            client_phone = body["from_number"]

        # lowercase variants (just in case API returns them)
        if not agent_phone and body.get("to"):
            agent_phone = body["to"]
        if not client_phone and body.get("from"):
            client_phone = body["from"]

        # Additional Twilio fields: Caller / Called
        if not agent_phone and body.get("Called"):
            agent_phone = body["Called"]
        if not client_phone and body.get("Caller"):
            client_phone = body["Caller"]

    # --- Source 3: metadata.phone_call ---
    phone_call = meta.get("phone_call", {})
    if phone_call and isinstance(phone_call, dict):
        if not agent_phone:
            agent_phone = phone_call.get("agent_number") or phone_call.get("to_number") or phone_call.get("to")
        if not client_phone:
            client_phone = phone_call.get("external_number") or phone_call.get("from_number") or phone_call.get("from")
        # Also try phone_number fields
        if not agent_phone:
            agent_phone = phone_call.get("agent_phone_number") or phone_call.get("called_number")
        if not client_phone:
            client_phone = phone_call.get("caller_phone_number") or phone_call.get("caller_number")

    # --- Source 4: conversation_initiation_client_data ---
    client_data = detail.get("conversation_initiation_client_data", {})
    if client_data and isinstance(client_data, dict):
        dyn = client_data.get("dynamic_variables", {})
        if dyn and isinstance(dyn, dict):
            if not agent_phone:
                agent_phone = (dyn.get("agent_number") or dyn.get("to_number")
                               or dyn.get("To") or dyn.get("agent_phone")
                               or dyn.get("called_number") or dyn.get("Called"))
            if not client_phone:
                client_phone = (dyn.get("customer_number") or dyn.get("from_number")
                                or dyn.get("From") or dyn.get("client_phone")
                                or dyn.get("caller_number") or dyn.get("Caller")
                                or dyn.get("phone") or dyn.get("phone_number")
                                or dyn.get("customer_phone"))

    # --- Source 5: Deep search in metadata for phone-related keys ---
    if (not agent_phone or not client_phone) and isinstance(meta, dict):
        deep_result = {}
        _deep_search_in_dict(meta, "agent_phone", "client_phone",
                             agent_phone, client_phone, deep_result)
        if not agent_phone and deep_result.get("agent"):
            agent_phone = deep_result["agent"]
        if not client_phone and deep_result.get("client"):
            client_phone = deep_result["client"]

    # --- Source 6: Deep recursive search in full detail as last resort ---
    if not agent_phone or not client_phone:
        phone_values = _deep_find_phone_values(detail)
        if phone_values:
            # Classify found phone values by path context
            for path, value in phone_values:
                path_lower = path.lower()
                if not agent_phone and any(kw in path_lower for kw in
                    ("agent", "to_number", ".to", "called", "voicebot", "bot_number")):
                    agent_phone = value
                elif not client_phone and any(kw in path_lower for kw in
                    ("client", "customer", "from_number", ".from", "caller", "external", "user_phone")):
                    client_phone = value

            # If still missing, assign first/second found phone generically
            if not agent_phone and not client_phone and len(phone_values) >= 2:
                agent_phone = phone_values[0][1]
                client_phone = phone_values[1][1]
            elif not agent_phone and not client_phone and len(phone_values) == 1:
                # Only one phone found - log it and assign to client (more common)
                client_phone = phone_values[0][1]

    # Normalize: strip whitespace
    if agent_phone:
        agent_phone = str(agent_phone).strip()
    if client_phone:
        client_phone = str(client_phone).strip()

    return agent_phone, client_phone


def _deep_search_in_dict(d: dict, agent_key_hint: str, client_key_hint: str,
                          existing_agent, existing_client, result: dict):
    """Search dict recursively for keys containing phone/number related names."""
    agent_keywords = {"agent_number", "to_number", "To", "Called", "agent_phone",
                      "called_number", "bot_number", "destination_number", "dialed_number",
                      "agent_phone_number", "to"}
    client_keywords = {"from_number", "From", "Caller", "external_number", "customer_number",
                       "caller_number", "client_phone", "source_number", "originating_number",
                       "customer_phone", "phone_number", "phone", "from", "caller_phone_number"}

    for k, v in d.items():
        if isinstance(v, dict):
            _deep_search_in_dict(v, agent_key_hint, client_key_hint,
                                existing_agent, existing_client, result)
        elif isinstance(v, str) and v.strip():
            if not existing_agent and not result.get("agent") and k in agent_keywords:
                result["agent"] = v.strip()
            if not existing_client and not result.get("client") and k in client_keywords:
                result["client"] = v.strip()


def _update_conversation_details(conv: Conversation, detail: dict):
    meta = detail.get("metadata", {})
    analysis = detail.get("analysis", {})

    conv.has_audio = detail.get("has_audio", False)
    conv.cost = meta.get("cost", 0)
    conv.termination_reason = meta.get("termination_reason")
    conv.user_id = detail.get("user_id")

    # Phone numbers - extract from multiple possible locations
    conv.agent_phone, conv.client_phone = _extract_phone_numbers(detail, meta)
    conv.call_successful = analysis.get("call_successful", conv.call_successful)
    conv.transcript_summary = analysis.get("transcript_summary", conv.transcript_summary)

    eval_criteria = analysis.get("evaluation_criteria_results")
    if eval_criteria:
        conv.evaluation_criteria_results = json.dumps(eval_criteria)

    data_collection = analysis.get("data_collection_results")
    if data_collection:
        conv.data_collection_results = json.dumps(data_collection)

    transcript = detail.get("transcript")
    if transcript:
        conv.transcript = json.dumps(transcript)

    # Update duration/message count from detail if available
    if meta.get("call_duration_secs"):
        conv.call_duration_secs = meta["call_duration_secs"]
    if meta.get("start_time_unix_secs"):
        conv.start_time_unix = meta["start_time_unix_secs"]

    conv.details_fetched = True
    conv.fetched_at = datetime.utcnow()


def compute_kpis(db: Session, agent_id: str, month: Optional[str] = None) -> dict:
    """Compute all KPIs for a given agent and optional month partition."""
    query = db.query(Conversation).filter(Conversation.agent_id == agent_id)
    if month:
        query = query.filter(Conversation.month_partition == month)

    conversations = query.all()
    total = len(conversations)

    if total == 0:
        return _empty_kpis(agent_id, month)

    # 1. Conversion rate (success)
    successful = sum(1 for c in conversations if c.call_successful == "success")
    failed = sum(1 for c in conversations if c.call_successful == "failure")
    unknown = sum(1 for c in conversations if c.call_successful == "unknown")

    # 2. Call attempts
    outbound = sum(1 for c in conversations if c.direction == "outbound")
    inbound = sum(1 for c in conversations if c.direction == "inbound")
    done_calls = sum(1 for c in conversations if c.status == "done")
    failed_calls = sum(1 for c in conversations if c.status == "failed")

    # 3. Evaluation criteria scoring
    criteria_stats = _compute_criteria_stats(conversations)

    # 4. Call duration
    durations = [c.call_duration_secs for c in conversations if c.call_duration_secs and c.call_duration_secs > 0]
    avg_duration = sum(durations) / len(durations) if durations else 0
    min_duration = min(durations) if durations else 0
    max_duration = max(durations) if durations else 0
    short_calls = sum(1 for d in durations if d < 30)
    long_calls = sum(1 for d in durations if d > 300)

    # 5. Transfers (termination_reason hints)
    transfers = sum(1 for c in conversations if c.termination_reason and "transfer" in c.termination_reason.lower())

    # 6. Additional KPIs
    dropouts = sum(1 for c in conversations if c.status in ("failed", "initiated") or
                   (c.termination_reason and "hang" in c.termination_reason.lower()))

    message_counts = [c.message_count for c in conversations if c.message_count and c.message_count > 0]
    avg_messages = sum(message_counts) / len(message_counts) if message_counts else 0

    costs = [c.cost for c in conversations if c.cost and c.cost > 0]
    total_cost = sum(costs)
    avg_cost = total_cost / len(costs) if costs else 0

    technical_errors = sum(1 for c in conversations if c.status == "failed")

    # Ratings
    ratings = [c.rating for c in conversations if c.rating is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else None

    # Trends by day
    daily_trends = _compute_daily_trends(conversations)

    return {
        "agent_id": agent_id,
        "month": month or "all",
        "total_conversations": total,
        # KPI 1
        "conversion_rate": round(successful / total * 100, 2) if total else 0,
        "successful_count": successful,
        "failed_count": failed,
        "unknown_count": unknown,
        # KPI 2
        "outbound_calls": outbound,
        "inbound_calls": inbound,
        "done_calls": done_calls,
        "failed_calls": failed_calls,
        "connection_rate": round(done_calls / total * 100, 2) if total else 0,
        # KPI 3
        "criteria_stats": criteria_stats,
        # KPI 4
        "avg_duration_secs": round(avg_duration, 1),
        "min_duration_secs": min_duration,
        "max_duration_secs": max_duration,
        "short_calls_under_30s": short_calls,
        "long_calls_over_300s": long_calls,
        # KPI 5
        "transfer_count": transfers,
        "transfer_rate": round(transfers / total * 100, 2) if total else 0,
        # KPI 6
        "dropout_count": dropouts,
        "dropout_rate": round(dropouts / total * 100, 2) if total else 0,
        "avg_message_count": round(avg_messages, 1),
        "total_cost": total_cost,
        "avg_cost_per_session": round(avg_cost, 2),
        "technical_errors": technical_errors,
        "error_rate": round(technical_errors / total * 100, 2) if total else 0,
        "avg_rating": round(avg_rating, 2) if avg_rating else None,
        # Trends
        "daily_trends": daily_trends,
    }


def _compute_criteria_stats(conversations: list) -> list:
    """Aggregate evaluation criteria across all conversations."""
    criteria_map = {}
    for c in conversations:
        if not c.evaluation_criteria_results:
            continue
        try:
            criteria = json.loads(c.evaluation_criteria_results)
            if isinstance(criteria, dict):
                for crit_id, result in criteria.items():
                    if crit_id not in criteria_map:
                        criteria_map[crit_id] = {"name": crit_id, "pass": 0, "fail": 0, "total": 0}
                    criteria_map[crit_id]["total"] += 1
                    if isinstance(result, dict):
                        if result.get("result") == "success":
                            criteria_map[crit_id]["pass"] += 1
                        else:
                            criteria_map[crit_id]["fail"] += 1
                    elif result == "success":
                        criteria_map[crit_id]["pass"] += 1
                    else:
                        criteria_map[crit_id]["fail"] += 1
            elif isinstance(criteria, list):
                for item in criteria:
                    crit_id = item.get("id") or item.get("criteria_id") or str(item)
                    if crit_id not in criteria_map:
                        criteria_map[crit_id] = {"name": crit_id, "pass": 0, "fail": 0, "total": 0}
                    criteria_map[crit_id]["total"] += 1
                    if item.get("result") == "success":
                        criteria_map[crit_id]["pass"] += 1
                    else:
                        criteria_map[crit_id]["fail"] += 1
        except (json.JSONDecodeError, TypeError):
            pass

    return list(criteria_map.values())


def _compute_daily_trends(conversations: list) -> list:
    """Group conversations by day and compute daily stats."""
    day_map = {}
    for c in conversations:
        if not c.start_time_unix:
            continue
        day_str = datetime.utcfromtimestamp(c.start_time_unix).strftime("%Y-%m-%d")
        if day_str not in day_map:
            day_map[day_str] = {"date": day_str, "total": 0, "success": 0, "failed": 0, "avg_duration": [], "cost": 0}
        day_map[day_str]["total"] += 1
        if c.call_successful == "success":
            day_map[day_str]["success"] += 1
        elif c.call_successful == "failure":
            day_map[day_str]["failed"] += 1
        if c.call_duration_secs:
            day_map[day_str]["avg_duration"].append(c.call_duration_secs)
        if c.cost:
            day_map[day_str]["cost"] += c.cost

    result = []
    for day_str in sorted(day_map.keys()):
        d = day_map[day_str]
        durations = d["avg_duration"]
        result.append({
            "date": day_str,
            "total": d["total"],
            "success": d["success"],
            "failed": d["failed"],
            "avg_duration": round(sum(durations) / len(durations), 1) if durations else 0,
            "cost": d["cost"],
        })
    return result


def _empty_kpis(agent_id: str, month: Optional[str]) -> dict:
    return {
        "agent_id": agent_id,
        "month": month or "all",
        "total_conversations": 0,
        "conversion_rate": 0, "successful_count": 0, "failed_count": 0, "unknown_count": 0,
        "outbound_calls": 0, "inbound_calls": 0, "done_calls": 0, "failed_calls": 0, "connection_rate": 0,
        "criteria_stats": [],
        "avg_duration_secs": 0, "min_duration_secs": 0, "max_duration_secs": 0,
        "short_calls_under_30s": 0, "long_calls_over_300s": 0,
        "transfer_count": 0, "transfer_rate": 0,
        "dropout_count": 0, "dropout_rate": 0,
        "avg_message_count": 0, "total_cost": 0, "avg_cost_per_session": 0,
        "technical_errors": 0, "error_rate": 0, "avg_rating": None,
        "daily_trends": [],
    }


def archive_month_to_csv(db: Session, agent_id: str, month_partition: str) -> Optional[str]:
    """Archive conversations for a given month to CSV. Returns file path."""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.agent_id == agent_id, Conversation.month_partition == month_partition)
        .all()
    )
    if not conversations:
        return None

    filename = f"conversations_{agent_id}_{month_partition}.csv"
    filepath = os.path.join(CSV_DIR, filename)

    fields = [
        "conversation_id", "agent_id", "agent_name", "status", "call_successful",
        "start_time_unix", "call_duration_secs", "message_count", "transcript_summary",
        "call_summary_title", "main_language", "direction", "rating", "tool_names",
        "agent_phone", "client_phone",
        "has_audio", "cost", "termination_reason", "user_id",
        "evaluation_criteria_results", "data_collection_results",
        "month_partition", "fetched_at",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for c in conversations:
            writer.writerow({field: getattr(c, field, "") for field in fields})

    # Log archive
    log = ArchiveLog(
        month_partition=month_partition,
        agent_id=agent_id,
        file_path=filepath,
        records_count=len(conversations),
    )
    db.add(log)
    db.commit()

    return filepath


def check_and_archive(db: Session):
    """Check if we're past the 5th day of month, archive previous month if not done."""
    now = datetime.utcnow()
    if now.day > 5:
        return  # only archive in first 5 days

    # Previous month
    first_of_month = now.replace(day=1)
    prev_month = (first_of_month - timedelta(days=1))
    prev_partition = prev_month.strftime("%Y-%m")

    # Get all agent_ids with data for that month
    agent_ids = (
        db.query(Conversation.agent_id)
        .filter(Conversation.month_partition == prev_partition)
        .distinct()
        .all()
    )

    for (agent_id,) in agent_ids:
        # Check if already archived
        existing = (
            db.query(ArchiveLog)
            .filter(ArchiveLog.month_partition == prev_partition, ArchiveLog.agent_id == agent_id)
            .first()
        )
        if existing:
            continue
        archive_month_to_csv(db, agent_id, prev_partition)
        logger.info(f"Archived {prev_partition} for agent {agent_id}")


def get_available_months(db: Session, agent_id: str) -> list[str]:
    """Get list of month partitions available for agent."""
    results = (
        db.query(Conversation.month_partition)
        .filter(Conversation.agent_id == agent_id)
        .distinct()
        .order_by(Conversation.month_partition.desc())
        .all()
    )
    return [r[0] for r in results]
