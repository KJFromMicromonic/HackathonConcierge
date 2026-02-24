"""
Session store for managing user threads.

Provides thread lifecycle management:
1. User connects → get_or_create_thread()
2. User switches thread → switch_thread()
3. User creates new → create_new_thread()
"""

import httpx
from typing import Dict, Optional
from app.config import get_settings


class SessionStore:
    """
    Manages user sessions and thread associations.

    Maps user_id → thread_id for Backboard conversations.
    In production, replace with Redis or database for persistence.
    """

    _instance: Optional["SessionStore"] = None

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
        self._sessions: Dict[str, str] = {}  # user_id -> current_thread_id
        self._client = httpx.Client(timeout=30)
        self._async_client: Optional[httpx.AsyncClient] = None

    @property
    def headers(self) -> dict:
        return {
            "X-API-Key": self.settings.backboard_api_key,
            "Content-Type": "application/json"
        }

    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=30)
        return self._async_client

    def _create_thread_sync(self) -> str:
        """Create a new Backboard thread (synchronous)."""
        resp = self._client.post(
            f"{self.settings.backboard_base_url}/assistants/{self.settings.backboard_assistant_id}/threads",
            headers=self.headers,
            json={}
        )
        resp.raise_for_status()
        return resp.json()["thread_id"]

    async def _create_thread_async(self) -> str:
        """Create a new Backboard thread (asynchronous)."""
        client = self._get_async_client()
        resp = await client.post(
            f"{self.settings.backboard_base_url}/assistants/{self.settings.backboard_assistant_id}/threads",
            headers=self.headers,
            json={}
        )
        resp.raise_for_status()
        return resp.json()["thread_id"]

    def get_or_create_thread(self, user_id: str) -> str:
        """
        Get existing thread for user or create a new one (synchronous).

        Args:
            user_id: Unique user identifier

        Returns:
            thread_id for Backboard conversation
        """
        if user_id in self._sessions:
            return self._sessions[user_id]

        # Create new thread
        try:
            thread_id = self._create_thread_sync()
            self._sessions[user_id] = thread_id
            print(f"[SessionStore] Created thread {thread_id} for user {user_id}")
            return thread_id
        except Exception as e:
            print(f"[SessionStore] Error creating thread: {e}")
            raise

    async def get_or_create_thread_async(self, user_id: str) -> str:
        """
        Get existing thread for user or create a new one (asynchronous).

        Args:
            user_id: Unique user identifier

        Returns:
            thread_id for Backboard conversation
        """
        if user_id in self._sessions:
            return self._sessions[user_id]

        # Create new thread
        try:
            thread_id = await self._create_thread_async()
            self._sessions[user_id] = thread_id
            print(f"[SessionStore] Created thread {thread_id} for user {user_id}")
            return thread_id
        except Exception as e:
            print(f"[SessionStore] Error creating thread: {e}")
            raise

    async def create_new_thread(self, user_id: str) -> str:
        """
        Create a new thread for user, replacing current one.

        Args:
            user_id: Unique user identifier

        Returns:
            New thread_id
        """
        try:
            thread_id = await self._create_thread_async()
            self._sessions[user_id] = thread_id
            print(f"[SessionStore] Created new thread {thread_id} for user {user_id}")
            return thread_id
        except Exception as e:
            print(f"[SessionStore] Error creating new thread: {e}")
            raise

    def switch_thread(self, user_id: str, thread_id: str) -> str:
        """
        Switch user to a different thread.

        Args:
            user_id: Unique user identifier
            thread_id: Thread ID to switch to

        Returns:
            The thread_id that was switched to
        """
        self._sessions[user_id] = thread_id
        print(f"[SessionStore] Switched user {user_id} to thread {thread_id}")
        return thread_id

    def get_thread(self, user_id: str) -> Optional[str]:
        """Get thread_id for user if exists, None otherwise."""
        return self._sessions.get(user_id)

    def get_current_thread(self, user_id: str) -> Optional[str]:
        """Alias for get_thread."""
        return self.get_thread(user_id)

    def clear_session(self, user_id: str) -> None:
        """Clear a user's session (creates new thread on next message)."""
        if user_id in self._sessions:
            del self._sessions[user_id]
            print(f"[SessionStore] Cleared session for user {user_id}")

    def close(self):
        """Clean up HTTP clients."""
        self._client.close()
        if self._async_client:
            # Note: async client should be closed in async context
            # This is a best-effort cleanup
            pass

    async def aclose(self):
        """Clean up HTTP clients (async version)."""
        self._client.close()
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None


# Singleton accessor
_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """Get or create the singleton session store."""
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
