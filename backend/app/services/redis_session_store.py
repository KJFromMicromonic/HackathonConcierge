"""
Redis-backed session store for production scaling.

Enables horizontal scaling across multiple backend pods by storing
user -> thread mappings in Redis instead of in-memory dict.

Usage:
    # In config, set REDIS_URL environment variable
    # Then use RedisSessionStore instead of SessionStore
"""

import httpx
from typing import Optional
from loguru import logger

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed. Install with: pip install redis")

from app.config import get_settings


class RedisSessionStore:
    """
    Redis-backed session store for multi-pod deployments.

    Provides the same interface as SessionStore but persists
    user -> thread_id mappings in Redis.

    Features:
    - TTL on sessions (default 24h) for automatic cleanup
    - Atomic operations for thread creation
    - Connection pooling for performance
    """

    _instance: Optional["RedisSessionStore"] = None

    # Session TTL in seconds (24 hours)
    SESSION_TTL = 86400

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        if not REDIS_AVAILABLE:
            raise RuntimeError("redis package required for RedisSessionStore")

        self.settings = get_settings()
        self._redis: Optional[redis.Redis] = None
        self._async_client: Optional[httpx.AsyncClient] = None
        self._key_prefix = "hackathon:session:"

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            redis_url = getattr(self.settings, 'redis_url', 'redis://localhost:6379/0')
            self._redis = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis

    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=30)
        return self._async_client

    @property
    def headers(self) -> dict:
        return {
            "X-API-Key": self.settings.backboard_api_key,
            "Content-Type": "application/json"
        }

    def _session_key(self, user_id: str) -> str:
        """Generate Redis key for user session."""
        return f"{self._key_prefix}{user_id}"

    async def _create_thread_async(self) -> str:
        """Create a new Backboard thread."""
        client = self._get_async_client()
        resp = await client.post(
            f"{self.settings.backboard_base_url}/assistants/{self.settings.backboard_assistant_id}/threads",
            headers=self.headers,
            json={}
        )
        resp.raise_for_status()
        return resp.json()["thread_id"]

    async def get_or_create_thread_async(self, user_id: str) -> str:
        """
        Get existing thread for user or create a new one.

        Uses Redis SETNX for atomic thread creation to prevent
        race conditions when multiple pods serve the same user.

        Args:
            user_id: Unique user identifier

        Returns:
            thread_id for Backboard conversation
        """
        r = await self._get_redis()
        key = self._session_key(user_id)

        # Check if thread exists
        thread_id = await r.get(key)
        if thread_id:
            # Refresh TTL on access
            await r.expire(key, self.SESSION_TTL)
            return thread_id

        # Create new thread (with lock to prevent race condition)
        lock_key = f"{key}:lock"
        lock = r.lock(lock_key, timeout=10)

        try:
            async with lock:
                # Double-check after acquiring lock
                thread_id = await r.get(key)
                if thread_id:
                    return thread_id

                # Create new thread
                thread_id = await self._create_thread_async()
                await r.setex(key, self.SESSION_TTL, thread_id)
                logger.info(f"[RedisSessionStore] Created thread {thread_id} for user {user_id}")
                return thread_id
        except Exception as e:
            logger.error(f"[RedisSessionStore] Error creating thread: {e}")
            raise

    # Sync wrapper for compatibility
    def get_or_create_thread(self, user_id: str) -> str:
        """Synchronous wrapper - prefer async version."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.get_or_create_thread_async(user_id)
        )

    async def create_new_thread(self, user_id: str) -> str:
        """
        Create a new thread for user, replacing current one.

        Args:
            user_id: Unique user identifier

        Returns:
            New thread_id
        """
        r = await self._get_redis()
        key = self._session_key(user_id)

        try:
            thread_id = await self._create_thread_async()
            await r.setex(key, self.SESSION_TTL, thread_id)
            logger.info(f"[RedisSessionStore] Created new thread {thread_id} for user {user_id}")
            return thread_id
        except Exception as e:
            logger.error(f"[RedisSessionStore] Error creating new thread: {e}")
            raise

    async def switch_thread(self, user_id: str, thread_id: str) -> str:
        """
        Switch user to a different thread.

        Args:
            user_id: Unique user identifier
            thread_id: Thread ID to switch to

        Returns:
            The thread_id that was switched to
        """
        r = await self._get_redis()
        key = self._session_key(user_id)
        await r.setex(key, self.SESSION_TTL, thread_id)
        logger.info(f"[RedisSessionStore] Switched user {user_id} to thread {thread_id}")
        return thread_id

    async def get_thread(self, user_id: str) -> Optional[str]:
        """Get thread_id for user if exists, None otherwise."""
        r = await self._get_redis()
        key = self._session_key(user_id)
        return await r.get(key)

    async def get_current_thread(self, user_id: str) -> Optional[str]:
        """Alias for get_thread."""
        return await self.get_thread(user_id)

    async def clear_session(self, user_id: str) -> None:
        """Clear a user's session (creates new thread on next message)."""
        r = await self._get_redis()
        key = self._session_key(user_id)
        await r.delete(key)
        logger.info(f"[RedisSessionStore] Cleared session for user {user_id}")

    async def aclose(self):
        """Clean up connections."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
        if self._redis:
            await self._redis.close()
            self._redis = None


# Singleton accessor
_redis_store: Optional[RedisSessionStore] = None


def get_redis_session_store() -> RedisSessionStore:
    """Get or create the singleton Redis session store."""
    global _redis_store
    if _redis_store is None:
        _redis_store = RedisSessionStore()
    return _redis_store
