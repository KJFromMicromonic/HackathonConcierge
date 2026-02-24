"""
Thread/session management for Backboard conversations.

Maps user_id → thread_id for the LiveKit agent.
Uses Supabase for persistence (shared with the chat backend)
with an in-memory cache for fast lookups within a session.
"""

import os
from typing import Dict, Optional

import httpx
from loguru import logger


class SessionStore:
    """
    Manages user → thread_id mappings for Backboard conversations.

    Checks Supabase first for existing threads (shared with chat mode),
    falls back to creating new threads on demand.
    Caches lookups in-memory for the duration of the agent session.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        assistant_id: str,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._assistant_id = assistant_id
        self._cache: Dict[str, str] = {}  # in-memory cache
        self._client: Optional[httpx.AsyncClient] = None

        # Supabase config
        self._supabase_url = os.getenv("SUPABASE_URL", "")
        self._supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")

    def set_assistant_id(self, assistant_id: str) -> None:
        """Update the assistant ID (for per-user assistants)."""
        self._assistant_id = assistant_id

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    @property
    def _supabase_headers(self) -> dict:
        return {
            "apikey": self._supabase_key,
            "Authorization": f"Bearer {self._supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def _check_supabase_thread(self, user_id: str) -> Optional[str]:
        """Check Supabase for an existing thread mapping."""
        if not self._supabase_url or not self._supabase_key:
            return None

        try:
            client = self._get_client()
            resp = await client.get(
                f"{self._supabase_url}/rest/v1/user_threads",
                headers=self._supabase_headers,
                params={"user_id": f"eq.{user_id}", "select": "thread_id"},
            )
            resp.raise_for_status()
            data = resp.json()
            if data and len(data) > 0:
                return data[0]["thread_id"]
        except Exception as e:
            logger.warning(f"[SessionStore] Supabase lookup failed: {e}")

        return None

    async def _store_supabase_thread(self, user_id: str, thread_id: str) -> None:
        """Store thread mapping in Supabase (upsert)."""
        if not self._supabase_url or not self._supabase_key:
            return

        try:
            client = self._get_client()
            resp = await client.post(
                f"{self._supabase_url}/rest/v1/user_threads",
                headers={
                    **self._supabase_headers,
                    "Prefer": "resolution=merge-duplicates,return=representation",
                },
                json={"user_id": user_id, "thread_id": thread_id},
            )
            resp.raise_for_status()
        except Exception as e:
            logger.warning(f"[SessionStore] Supabase store failed: {e}")

    async def _create_thread(self) -> str:
        """Create a new Backboard thread."""
        client = self._get_client()
        resp = await client.post(
            f"{self._base_url}/assistants/{self._assistant_id}/threads",
            headers={
                "X-API-Key": self._api_key,
                "Content-Type": "application/json",
            },
            json={},
        )
        resp.raise_for_status()
        return resp.json()["thread_id"]

    async def get_or_create_thread(self, user_id: str) -> str:
        """Get existing thread or create a new one for this user."""
        # Check in-memory cache
        if user_id in self._cache:
            return self._cache[user_id]

        # Check Supabase (shared with chat backend)
        thread_id = await self._check_supabase_thread(user_id)
        if thread_id:
            self._cache[user_id] = thread_id
            logger.info(f"[SessionStore] Found existing thread {thread_id} for user {user_id}")
            return thread_id

        # Create new thread
        thread_id = await self._create_thread()
        self._cache[user_id] = thread_id

        # Persist to Supabase
        await self._store_supabase_thread(user_id, thread_id)

        logger.info(f"[SessionStore] Created thread {thread_id} for user {user_id}")
        return thread_id

    async def create_new_thread(self, user_id: str) -> str:
        """Force-create a new thread, replacing the current one."""
        thread_id = await self._create_thread()
        self._cache[user_id] = thread_id
        await self._store_supabase_thread(user_id, thread_id)
        logger.info(f"[SessionStore] New thread {thread_id} for user {user_id}")
        return thread_id

    def get_thread(self, user_id: str) -> Optional[str]:
        """Get thread_id for user from cache, or None."""
        return self._cache.get(user_id)

    def clear_session(self, user_id: str) -> None:
        """Remove a user's session from cache."""
        self._cache.pop(user_id, None)

    async def aclose(self) -> None:
        """Clean up HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
