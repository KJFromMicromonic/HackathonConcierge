"""
Supabase-backed session store for user thread management.

Stores user_id → thread_id mappings in PostgreSQL via Supabase.
Provides persistence and works across multiple backend instances.

Now supports per-user assistants: each user has their own Backboard
assistant with isolated memories and shared hackathon documents.
"""

import httpx
from typing import Optional
from loguru import logger

from app.config import get_settings


class SupabaseSessionStore:
    """
    Session store using Supabase PostgreSQL.

    Table: user_threads
    - user_id (UUID, PK) - references auth.users
    - thread_id (TEXT) - Backboard thread ID
    - created_at, updated_at (TIMESTAMPTZ)
    """

    _instance: Optional["SupabaseSessionStore"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None

    @property
    def _headers(self) -> dict:
        """Headers for Supabase REST API."""
        return {
            "apikey": self.settings.supabase_service_key,
            "Authorization": f"Bearer {self.settings.supabase_service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    @property
    def _base_url(self) -> str:
        """Supabase REST API base URL."""
        return f"{self.settings.supabase_url}/rest/v1"

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    def _get_sync_client(self) -> httpx.Client:
        """Get or create sync HTTP client."""
        if self._sync_client is None:
            self._sync_client = httpx.Client(timeout=30)
        return self._sync_client

    @property
    def _backboard_headers(self) -> dict:
        """Headers for Backboard API."""
        return {
            "X-API-Key": self.settings.backboard_api_key,
            "Content-Type": "application/json"
        }

    async def _get_or_create_user_assistant(self, user_id: str) -> str:
        """Get the user's personal assistant ID, or create one if needed."""
        client = self._get_client()

        # Check if user already has an assistant
        try:
            resp = await client.get(
                f"{self._base_url}/user_assistants",
                headers=self._headers,
                params={"user_id": f"eq.{user_id}", "select": "assistant_id"}
            )
            resp.raise_for_status()
            data = resp.json()
            if data and len(data) > 0:
                return data[0]["assistant_id"]
        except Exception as e:
            logger.error(f"Error checking user assistant: {e}")

        # No assistant - auto-provision one
        logger.info(f"Auto-provisioning assistant for user {user_id}")
        from app.services.user_assistant_service import get_user_assistant_service
        assistant_service = get_user_assistant_service()
        return await assistant_service.create_assistant_for_user(user_id)

    async def _create_thread_async(self, user_id: str) -> str:
        """Create a new Backboard thread for the user's assistant."""
        client = self._get_client()

        # Get or create user's personal assistant (auto-provisions if needed)
        assistant_id = await self._get_or_create_user_assistant(user_id)

        logger.debug(f"Creating thread for user {user_id} on assistant {assistant_id}")

        resp = await client.post(
            f"{self.settings.backboard_base_url}/assistants/{assistant_id}/threads",
            headers=self._backboard_headers,
            json={}
        )
        resp.raise_for_status()
        return resp.json()["thread_id"]

    def _create_thread_sync(self, user_id: str) -> str:
        """Create a new Backboard thread (synchronous).

        NOTE: Sync path cannot do per-user assistant provisioning.
        It checks Supabase for an existing assistant, and fails loudly
        if none exists (forcing callers to use the async path).
        """
        client = self._get_sync_client()

        # Look up user's assistant from Supabase
        resp = client.get(
            f"{self._base_url}/user_assistants",
            headers=self._headers,
            params={"user_id": f"eq.{user_id}", "select": "assistant_id"}
        )
        resp.raise_for_status()
        data = resp.json()

        if data and len(data) > 0:
            assistant_id = data[0]["assistant_id"]
        else:
            raise RuntimeError(
                f"No assistant found for user {user_id}. "
                "Use the async path (get_or_create_thread_async) for auto-provisioning."
            )

        resp = client.post(
            f"{self.settings.backboard_base_url}/assistants/{assistant_id}/threads",
            headers=self._backboard_headers,
            json={}
        )
        resp.raise_for_status()
        return resp.json()["thread_id"]

    async def get_thread(self, user_id: str) -> Optional[str]:
        """Get thread_id for user if exists."""
        client = self._get_client()
        url = f"{self._base_url}/user_threads"
        logger.debug(f"[SupabaseSessionStore] GET {url} for user {user_id}")

        try:
            resp = await client.get(
                url,
                headers=self._headers,
                params={"user_id": f"eq.{user_id}", "select": "thread_id"}
            )
            resp.raise_for_status()
            data = resp.json()

            if data and len(data) > 0:
                return data[0]["thread_id"]
            return None
        except Exception as e:
            logger.error(f"[SupabaseSessionStore] Error getting thread: {e}")
            raise

    async def get_or_create_thread_async(self, user_id: str) -> str:
        """Get existing thread or create a new one."""
        # Check if thread exists
        thread_id = await self.get_thread(user_id)
        if thread_id:
            return thread_id

        # Create new Backboard thread (uses user's personal assistant)
        thread_id = await self._create_thread_async(user_id)

        # Store mapping in Supabase
        client = self._get_client()
        resp = await client.post(
            f"{self._base_url}/user_threads",
            headers=self._headers,
            json={"user_id": user_id, "thread_id": thread_id}
        )
        resp.raise_for_status()

        logger.info(f"[SupabaseSessionStore] Created thread {thread_id} for user {user_id}")
        return thread_id

    def get_or_create_thread(self, user_id: str) -> str:
        """Synchronous version for compatibility."""
        # Check if thread exists
        client = self._get_sync_client()

        resp = client.get(
            f"{self._base_url}/user_threads",
            headers=self._headers,
            params={"user_id": f"eq.{user_id}", "select": "thread_id"}
        )
        resp.raise_for_status()
        data = resp.json()

        if data and len(data) > 0:
            return data[0]["thread_id"]

        # Create new Backboard thread (sync uses global assistant)
        thread_id = self._create_thread_sync(user_id)

        # Store mapping in Supabase
        resp = client.post(
            f"{self._base_url}/user_threads",
            headers=self._headers,
            json={"user_id": user_id, "thread_id": thread_id}
        )
        resp.raise_for_status()

        logger.info(f"[SupabaseSessionStore] Created thread {thread_id} for user {user_id}")
        return thread_id

    async def create_new_thread(self, user_id: str) -> str:
        """Create a new thread, replacing current one."""
        thread_id = await self._create_thread_async(user_id)

        client = self._get_client()

        # Upsert: insert or update if exists
        resp = await client.post(
            f"{self._base_url}/user_threads",
            headers={**self._headers, "Prefer": "resolution=merge-duplicates,return=representation"},
            json={"user_id": user_id, "thread_id": thread_id}
        )
        resp.raise_for_status()

        logger.info(f"[SupabaseSessionStore] Created new thread {thread_id} for user {user_id}")
        return thread_id

    async def switch_thread(self, user_id: str, thread_id: str) -> str:
        """Switch user to a different thread."""
        client = self._get_client()

        # Upsert
        resp = await client.post(
            f"{self._base_url}/user_threads",
            headers={**self._headers, "Prefer": "resolution=merge-duplicates,return=representation"},
            json={"user_id": user_id, "thread_id": thread_id}
        )
        resp.raise_for_status()

        logger.info(f"[SupabaseSessionStore] Switched user {user_id} to thread {thread_id}")
        return thread_id

    async def clear_session(self, user_id: str) -> None:
        """Clear a user's session."""
        client = self._get_client()

        resp = await client.delete(
            f"{self._base_url}/user_threads",
            headers=self._headers,
            params={"user_id": f"eq.{user_id}"}
        )
        resp.raise_for_status()
        logger.info(f"[SupabaseSessionStore] Cleared session for user {user_id}")

    async def aclose(self):
        """Clean up HTTP clients."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None


# Singleton accessor
_supabase_store: Optional[SupabaseSessionStore] = None


def get_supabase_session_store() -> SupabaseSessionStore:
    """Get or create the singleton Supabase session store."""
    global _supabase_store
    if _supabase_store is None:
        _supabase_store = SupabaseSessionStore()
    return _supabase_store
