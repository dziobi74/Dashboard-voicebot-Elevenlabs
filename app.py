"""Main FastAPI application with scheduler, API endpoints, and dashboard."""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, Depends, HTTPException, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import BaseModel

from database import init_db, get_db, SessionLocal, AppSettings, Conversation, SyncLog, ArchiveLog
from sync_service import (
    sync_conversations, compute_kpis, get_setting, set_setting,
    get_agents, set_agents,
    check_and_archive, get_available_months, archive_month_to_csv,
    CSV_DIR,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Voicebot Dashboard", version="1.0.0")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

scheduler = AsyncIOScheduler()


# ─── Startup / Shutdown ───────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()
    scheduler.add_job(scheduled_sync, "cron", hour=2, minute=0, id="daily_sync")
    scheduler.add_job(scheduled_archive_check, "cron", day="1-5", hour=3, minute=0, id="archive_check")
    scheduler.start()
    logger.info("Scheduler started: daily sync at 02:00, archive check days 1-5 at 03:00")


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown(wait=False)


# ─── Scheduled Jobs ───────────────────────────────────────────────────

async def scheduled_sync():
    """Daily incremental sync for ALL configured agents."""
    db = SessionLocal()
    try:
        api_key = get_setting(db, "api_key")
        agents = get_agents(db)
        if not api_key or not agents:
            logger.warning("Scheduled sync skipped: API key or agents not configured")
            return

        now = datetime.utcnow()
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_unix = int(first_of_month.timestamp())
        end_unix = int(now.timestamp())

        for agent in agents:
            try:
                await sync_conversations(
                    agent_id=agent["id"],
                    api_key=api_key,
                    start_unix=start_unix,
                    end_unix=end_unix,
                    sync_type="scheduled",
                )
                logger.info(
                    f"Scheduled sync completed for agent {agent.get('name', '')} "
                    f"({agent['id'][:12]}) "
                    f"({first_of_month.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d %H:%M')})"
                )
            except Exception as e:
                logger.error(f"Scheduled sync failed for agent {agent.get('name', '')}: {e}")
            await asyncio.sleep(2)  # rate-limit between agents
    except Exception as e:
        logger.error(f"Scheduled sync failed: {e}")
    finally:
        db.close()


async def scheduled_archive_check():
    """Archive previous month data to CSV on days 1-5."""
    db = SessionLocal()
    try:
        check_and_archive(db)
    except Exception as e:
        logger.error(f"Archive check failed: {e}")
    finally:
        db.close()


# ─── Pydantic Models ─────────────────────────────────────────────────

class AgentItem(BaseModel):
    id: str
    name: str


class SettingsUpdate(BaseModel):
    api_key: str
    agents: list[AgentItem]


class SyncRequest(BaseModel):
    agent_id: Optional[str] = None
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD


# ─── HTML Pages ───────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    api_key = get_setting(db, "api_key")
    agents = get_agents(db)
    configured = bool(api_key and agents)
    first_agent_id = agents[0]["id"] if agents else None
    months = get_available_months(db, first_agent_id) if first_agent_id else []
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "configured": configured,
        "agents": agents,
        "agents_json": json.dumps(agents, ensure_ascii=False),
        "api_key_set": bool(api_key),
        "months": months,
    })


# ─── API Endpoints ────────────────────────────────────────────────────

@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate, db: Session = Depends(get_db)):
    if len(settings.agents) > 10:
        raise HTTPException(400, "Maksymalnie 10 agentów")
    if len(settings.agents) == 0:
        raise HTTPException(400, "Podaj przynajmniej jednego agenta")
    set_setting(db, "api_key", settings.api_key)
    set_agents(db, [a.model_dump() for a in settings.agents])
    return {"status": "ok", "message": "Zapisano ustawienia"}


@app.get("/api/settings")
async def get_settings_endpoint(db: Session = Depends(get_db)):
    api_key = get_setting(db, "api_key")
    agents = get_agents(db)
    return {
        "api_key_set": bool(api_key),
        "api_key_masked": f"{api_key[:4]}...{api_key[-4:]}" if api_key and len(api_key) > 8 else "****",
        "agents": agents,
    }


@app.get("/api/agents")
async def list_agents_endpoint(db: Session = Depends(get_db)):
    return {"agents": get_agents(db)}


@app.post("/api/sync")
async def trigger_sync(req: SyncRequest, db: Session = Depends(get_db)):
    api_key = get_setting(db, "api_key")
    if not api_key:
        raise HTTPException(400, "API key nie skonfigurowany")

    agents = get_agents(db)
    if not agents:
        raise HTTPException(400, "Brak skonfigurowanych agentów")

    start_unix = None
    end_unix = None
    if req.start_date:
        start_unix = int(datetime.strptime(req.start_date, "%Y-%m-%d").timestamp())
    if req.end_date:
        end_unix = int(
            (datetime.strptime(req.end_date, "%Y-%m-%d") + timedelta(days=1)).timestamp()
        )

    if req.agent_id:
        # Sync single specified agent
        asyncio.create_task(_run_sync(req.agent_id, api_key, start_unix, end_unix))
        return {"status": "started", "message": f"Synchronizacja agenta uruchomiona", "agents_count": 1}
    else:
        # Sync ALL configured agents
        for agent in agents:
            asyncio.create_task(_run_sync(agent["id"], api_key, start_unix, end_unix))
        return {"status": "started", "message": f"Synchronizacja {len(agents)} agentów uruchomiona", "agents_count": len(agents)}


async def _run_sync(agent_id, api_key, start_unix, end_unix):
    try:
        result = await sync_conversations(
            agent_id=agent_id,
            api_key=api_key,
            start_unix=start_unix,
            end_unix=end_unix,
            sync_type="manual",
        )
        logger.info(f"Manual sync completed for {agent_id[:12]}: {result}")
    except Exception as e:
        logger.error(f"Manual sync failed for {agent_id[:12]}: {e}")


@app.get("/api/kpis")
async def get_kpis(
    agent_id: str = Query(..., description="Agent ID"),
    month: Optional[str] = None,
    db: Session = Depends(get_db),
):
    kpis = compute_kpis(db, agent_id, month)
    return kpis


@app.get("/api/conversations")
async def list_conversations(
    agent_id: str = Query(..., description="Agent ID"),
    month: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Conversation).filter(Conversation.agent_id == agent_id)
    if month:
        query = query.filter(Conversation.month_partition == month)
    query = query.order_by(Conversation.start_time_unix.desc())

    total = query.count()
    conversations = query.offset((page - 1) * per_page).limit(per_page).all()

    # Collect all unique criteria IDs across the page for column headers
    all_criteria_ids = set()
    parsed_criteria = {}
    for c in conversations:
        if c.evaluation_criteria_results:
            try:
                ecr = json.loads(c.evaluation_criteria_results)
                if isinstance(ecr, dict):
                    parsed_criteria[c.conversation_id] = ecr
                    all_criteria_ids.update(ecr.keys())
            except (json.JSONDecodeError, TypeError):
                pass

    sorted_criteria_ids = sorted(all_criteria_ids)

    conv_list = []
    for c in conversations:
        ecr = parsed_criteria.get(c.conversation_id, {})
        criteria_results = {}
        for crit_id in sorted_criteria_ids:
            crit = ecr.get(crit_id)
            if crit and isinstance(crit, dict):
                criteria_results[crit_id] = crit.get("result", None)
            else:
                criteria_results[crit_id] = None

        conv_list.append({
            "conversation_id": c.conversation_id,
            "agent_name": c.agent_name,
            "status": c.status,
            "call_successful": c.call_successful,
            "start_time": datetime.utcfromtimestamp(c.start_time_unix).isoformat() if c.start_time_unix else None,
            "duration_secs": c.call_duration_secs,
            "message_count": c.message_count,
            "direction": c.direction,
            "agent_phone": c.agent_phone,
            "client_phone": c.client_phone,
            "conversation_source": c.conversation_initiation_source,
            "rating": c.rating,
            "termination_reason": c.termination_reason,
            "cost": c.cost,
            "transcript_summary": c.transcript_summary,
            "criteria": criteria_results,
        })

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "criteria_columns": sorted_criteria_ids,
        "conversations": conv_list,
    }


@app.get("/api/sync-logs")
async def list_sync_logs(db: Session = Depends(get_db)):
    logs = db.query(SyncLog).order_by(SyncLog.started_at.desc()).limit(50).all()
    return [
        {
            "id": l.id,
            "agent_id": l.agent_id,
            "sync_type": l.sync_type,
            "started_at": l.started_at.isoformat() if l.started_at else None,
            "finished_at": l.finished_at.isoformat() if l.finished_at else None,
            "conversations_fetched": l.conversations_fetched,
            "details_fetched": l.details_fetched,
            "status": l.status,
            "error_message": l.error_message,
        }
        for l in logs
    ]


@app.get("/api/months")
async def list_months(
    agent_id: str = Query(..., description="Agent ID"),
    db: Session = Depends(get_db),
):
    return {"months": get_available_months(db, agent_id)}


@app.post("/api/archive")
async def trigger_archive(
    month: str = Query(...),
    agent_id: str = Query(..., description="Agent ID"),
    db: Session = Depends(get_db),
):
    filepath = archive_month_to_csv(db, agent_id, month)
    if not filepath:
        raise HTTPException(404, "Brak konwersacji dla tego miesiąca i agenta")
    return {"status": "ok", "file": filepath}


@app.get("/api/archives")
async def list_archives(db: Session = Depends(get_db)):
    logs = db.query(ArchiveLog).order_by(ArchiveLog.archived_at.desc()).all()
    return [
        {
            "id": a.id,
            "month": a.month_partition,
            "agent_id": a.agent_id,
            "file_path": a.file_path,
            "records_count": a.records_count,
            "archived_at": a.archived_at.isoformat() if a.archived_at else None,
        }
        for a in logs
    ]


@app.post("/api/refetch-details")
async def refetch_details(
    agent_id: str = Query(..., description="Agent ID"),
    db: Session = Depends(get_db),
):
    """Reset details_fetched flag for conversations missing phone numbers, so next sync re-fetches them."""
    api_key = get_setting(db, "api_key")
    if not api_key:
        raise HTTPException(400, "API key nie skonfigurowany")

    # Reset details_fetched for conversations that have no phone numbers
    updated = (
        db.query(Conversation)
        .filter(
            Conversation.agent_id == agent_id,
            Conversation.details_fetched == True,
            (Conversation.agent_phone == None) | (Conversation.agent_phone == ""),
            (Conversation.client_phone == None) | (Conversation.client_phone == ""),
        )
        .update({Conversation.details_fetched: False}, synchronize_session="fetch")
    )
    db.commit()

    if updated > 0:
        # Auto-trigger sync in background
        now = datetime.utcnow()
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        asyncio.create_task(_run_sync(agent_id, api_key, int(first_of_month.timestamp()), int(now.timestamp())))

    return {"status": "ok", "conversations_reset": updated, "message": f"Zresetowano {updated} konwersacji. Ponowne pobieranie szczegółów uruchomione."}


@app.get("/api/download-csv/{archive_id}")
async def download_csv(archive_id: int, db: Session = Depends(get_db)):
    archive = db.query(ArchiveLog).filter(ArchiveLog.id == archive_id).first()
    if not archive or not os.path.exists(archive.file_path):
        raise HTTPException(404, "Archive not found")
    return FileResponse(archive.file_path, media_type="text/csv", filename=os.path.basename(archive.file_path))


@app.get("/api/debug-metadata")
async def debug_metadata(
    agent_id: str = Query(..., description="Agent ID"),
    conversation_id: Optional[str] = None,
    limit: int = 5,
    db: Session = Depends(get_db),
):
    """
    Diagnostic endpoint: fetch raw JSON detail from ElevenLabs API for
    conversations and find ALL keys/paths that contain phone-like values.
    Useful for discovering where phone numbers actually reside.
    """
    import re
    from elevenlabs_client import ElevenLabsClient

    api_key = get_setting(db, "api_key")
    if not api_key:
        raise HTTPException(400, "API key nie skonfigurowany")

    client = ElevenLabsClient(api_key)

    # Collect conversations to inspect
    if conversation_id:
        conv_ids = [conversation_id]
    else:
        # Pick some with phone numbers and some without
        with_phones = (
            db.query(Conversation.conversation_id)
            .filter(
                Conversation.agent_id == agent_id,
                Conversation.agent_phone != None,
                Conversation.agent_phone != "",
            )
            .limit(2)
            .all()
        )
        without_phones = (
            db.query(Conversation.conversation_id)
            .filter(
                Conversation.agent_id == agent_id,
                (Conversation.agent_phone == None) | (Conversation.agent_phone == ""),
            )
            .limit(3)
            .all()
        )
        conv_ids = [r[0] for r in with_phones] + [r[0] for r in without_phones]

    phone_pattern = re.compile(r'(\+?\d[\d\s\-]{6,15}\d)')

    def find_phone_paths(obj, path=""):
        """Recursively find all paths in JSON that contain phone-like values."""
        results = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                results.extend(find_phone_paths(v, new_path))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                new_path = f"{path}[{i}]"
                results.extend(find_phone_paths(v, new_path))
        elif isinstance(obj, str):
            if phone_pattern.search(obj):
                results.append({"path": path, "value": obj})
            # Also flag phone-related key names
            lower_path = path.lower()
            if any(kw in lower_path for kw in ("phone", "number", "caller", "called", "from", "to", "sip", "dial", "tel")):
                results.append({"path": path, "value": str(obj), "reason": "phone-related key name"})
        elif isinstance(obj, (int, float)):
            s = str(obj)
            if len(s) >= 8 and phone_pattern.search(s):
                results.append({"path": path, "value": s, "reason": "numeric phone-like"})
        return results

    diagnostics = []
    for cid in conv_ids[:limit]:
        try:
            detail = await client.get_conversation_detail(cid)
            # Find all phone-like paths
            phone_paths = find_phone_paths(detail)
            # Also dump top-level metadata structure
            meta = detail.get("metadata", {})
            meta_keys = list(meta.keys()) if isinstance(meta, dict) else str(type(meta))
            body = meta.get("body", {}) if isinstance(meta, dict) else {}
            body_keys = list(body.keys()) if isinstance(body, dict) else str(type(body))

            # Check conversation_initiation_client_data
            cicd = detail.get("conversation_initiation_client_data", {})
            cicd_keys = list(cicd.keys()) if isinstance(cicd, dict) else str(type(cicd))

            # Dump entire metadata and cicd as raw JSON for inspection
            diagnostics.append({
                "conversation_id": cid,
                "has_phone_in_db": bool(
                    db.query(Conversation)
                    .filter(
                        Conversation.conversation_id == cid,
                        Conversation.agent_phone != None,
                        Conversation.agent_phone != "",
                    )
                    .first()
                ),
                "phone_paths_found": phone_paths,
                "metadata_keys": meta_keys,
                "metadata_body_keys": body_keys,
                "metadata_body_raw": body if isinstance(body, dict) else str(body),
                "metadata_phone_call": meta.get("phone_call") if isinstance(meta, dict) else None,
                "cicd_keys": cicd_keys,
                "cicd_dynamic_variables": cicd.get("dynamic_variables") if isinstance(cicd, dict) else None,
                "full_metadata_raw": meta,
            })
            await asyncio.sleep(0.2)
        except Exception as e:
            diagnostics.append({"conversation_id": cid, "error": str(e)})

    return {"diagnostics": diagnostics, "total_checked": len(diagnostics)}


@app.get("/api/export-csv")
async def export_csv_on_demand(
    agent_id: str = Query(..., description="Agent ID"),
    month: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Export currently filtered conversations to CSV on demand (no pagination limit)."""
    import csv as csv_mod
    import io
    import tempfile

    query = db.query(Conversation).filter(Conversation.agent_id == agent_id)
    if month:
        query = query.filter(Conversation.month_partition == month)
    query = query.order_by(Conversation.start_time_unix.desc())

    conversations = query.all()
    if not conversations:
        raise HTTPException(404, "Brak danych do eksportu")

    fields = [
        "conversation_id", "agent_id", "agent_name", "status", "call_successful",
        "start_time_unix", "call_duration_secs", "message_count",
        "direction", "conversation_initiation_source", "agent_phone", "client_phone",
        "rating", "cost", "termination_reason",
        "transcript_summary", "call_summary_title",
        "main_language", "tool_names",
        "data_collection_results",
        "month_partition",
    ]

    # Collect all criteria IDs for separate columns
    all_criteria_ids = set()
    parsed_criteria = {}
    for c in conversations:
        if c.evaluation_criteria_results:
            try:
                ecr = json.loads(c.evaluation_criteria_results)
                if isinstance(ecr, dict):
                    parsed_criteria[c.conversation_id] = ecr
                    all_criteria_ids.update(ecr.keys())
            except (json.JSONDecodeError, TypeError):
                pass
    sorted_criteria_ids = sorted(all_criteria_ids)

    # Add human-readable date column + criteria columns
    header = ["data_rozmowy"] + fields + [f"kryterium_{cid}" for cid in sorted_criteria_ids]

    suffix = f"_{month}" if month else "_all"
    filename = f"export_{agent_id[:12]}{suffix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(CSV_DIR, filename)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv_mod.writer(f, delimiter=";")
        writer.writerow(header)
        for c in conversations:
            date_str = (
                datetime.utcfromtimestamp(c.start_time_unix).strftime("%Y-%m-%d %H:%M:%S")
                if c.start_time_unix else ""
            )
            base_row = [date_str] + [getattr(c, field, "") or "" for field in fields]
            ecr = parsed_criteria.get(c.conversation_id, {})
            criteria_row = []
            result_map = {"success": "2", "failure": "0", "unknown": "1"}
            for cid in sorted_criteria_ids:
                crit = ecr.get(cid)
                raw = crit.get("result", "") if isinstance(crit, dict) else ""
                criteria_row.append(result_map.get(raw, raw))
            writer.writerow(base_row + criteria_row)

    return FileResponse(
        filepath,
        media_type="text/csv",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
