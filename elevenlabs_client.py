"""ElevenLabs Conversational AI API client."""

import time
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.elevenlabs.io/v1/convai"


class ElevenLabsClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"xi-api-key": api_key}

    async def list_conversations(
        self,
        agent_id: str,
        start_after_unix: Optional[int] = None,
        start_before_unix: Optional[int] = None,
        page_size: int = 100,
        cursor: Optional[str] = None,
        call_successful: Optional[str] = None,
    ) -> dict:
        params = {
            "agent_id": agent_id,
            "page_size": page_size,
            "summary_mode": "include",
        }
        if start_after_unix:
            params["call_start_after_unix"] = start_after_unix
        if start_before_unix:
            params["call_start_before_unix"] = start_before_unix
        if cursor:
            params["cursor"] = cursor
        if call_successful:
            params["call_successful"] = call_successful

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{BASE_URL}/conversations",
                headers=self.headers,
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_conversation_detail(self, conversation_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{BASE_URL}/conversations/{conversation_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def fetch_all_conversations(
        self,
        agent_id: str,
        start_after_unix: Optional[int] = None,
        start_before_unix: Optional[int] = None,
    ) -> list[dict]:
        all_conversations = []
        cursor = None
        while True:
            data = await self.list_conversations(
                agent_id=agent_id,
                start_after_unix=start_after_unix,
                start_before_unix=start_before_unix,
                cursor=cursor,
            )
            conversations = data.get("conversations", [])
            all_conversations.extend(conversations)
            logger.info(f"Fetched page with {len(conversations)} conversations (total: {len(all_conversations)})")

            if not data.get("has_more", False):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break
            # small delay to avoid rate limits
            await _async_sleep(0.2)

        return all_conversations


async def _async_sleep(seconds: float):
    import asyncio
    await asyncio.sleep(seconds)
