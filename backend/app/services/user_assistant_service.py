"""
User Assistant Service - Creates and manages per-user Backboard assistants.

Each user gets their own assistant with:
1. Shared hackathon documents (uploaded on creation)
2. Isolated memories
3. Thread-level personal documents
"""

import asyncio
import httpx
from typing import Optional, Callable, Awaitable
from collections import defaultdict
from loguru import logger

from app.config import get_settings
from app.assistant_template import (
    SYSTEM_PROMPT,
    SHARED_DOCUMENTS,
    SHARED_DOCS_DIR,
    ASSISTANT_CONFIG,
)

# Type for the progress callback
ProgressCallback = Optional[Callable[[str, str, int, int], Awaitable[None]]]


class UserAssistantService:
    """
    Manages per-user Backboard assistants.

    Flow:
    1. User connects → get_or_create_assistant()
    2. Creates new Backboard assistant with system prompt
    3. Uploads all shared docs to the assistant
    4. Verifies docs are indexed
    5. Stores assistant_id in Supabase user_assistants table
    """

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._provision_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60)
        return self._client

    @property
    def _headers(self) -> dict:
        return {
            "X-API-Key": self.settings.backboard_api_key,
            "Content-Type": "application/json"
        }

    @property
    def _supabase_headers(self) -> dict:
        return {
            "apikey": self.settings.supabase_service_key,
            "Authorization": f"Bearer {self.settings.supabase_service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    async def get_user_assistant(self, user_id: str) -> Optional[str]:
        """Get assistant_id for a user from Supabase."""
        client = self._get_client()

        try:
            resp = await client.get(
                f"{self.settings.supabase_url}/rest/v1/user_assistants",
                headers=self._supabase_headers,
                params={"user_id": f"eq.{user_id}", "select": "assistant_id"}
            )
            resp.raise_for_status()
            data = resp.json()

            if data and len(data) > 0:
                return data[0]["assistant_id"]
            return None
        except Exception as e:
            logger.error(f"Error getting user assistant: {e}")
            return None

    async def create_assistant_for_user(
        self,
        user_id: str,
        user_name: Optional[str] = None,
        on_progress: ProgressCallback = None,
    ) -> str:
        """
        Create a new Backboard assistant for a user.

        1. Creates assistant with system prompt
        2. Uploads shared documents (with progress)
        3. Verifies document indexing
        4. Stores mapping in Supabase

        Args:
            on_progress: async callback(step, message, progress, total)

        Returns: assistant_id
        """
        client = self._get_client()

        # Check if user already has an assistant
        existing = await self.get_user_assistant(user_id)
        if existing:
            logger.info(f"User {user_id} already has assistant {existing}")
            return existing

        # Step 1: Create assistant
        if on_progress:
            await on_progress("creating_assistant", "Setting up your personal AI assistant...", 0, 0)

        assistant_name = f"AURA - {user_name}" if user_name else ASSISTANT_CONFIG["name"]

        logger.info(f"Creating assistant for user {user_id}")
        resp = await client.post(
            f"{self.settings.backboard_base_url}/assistants",
            headers=self._headers,
            json={
                "name": assistant_name,
                "description": ASSISTANT_CONFIG["description"],
                "system_prompt": SYSTEM_PROMPT,
                "embedding_provider": ASSISTANT_CONFIG.get("embedding_provider"),
                "embedding_model_name": ASSISTANT_CONFIG.get("embedding_model_name"),
                "embedding_dims": ASSISTANT_CONFIG.get("embedding_dims"),
            }
        )
        resp.raise_for_status()
        assistant_data = resp.json()
        assistant_id = assistant_data["assistant_id"]

        logger.info(f"Created assistant {assistant_id} for user {user_id}")

        # Step 2: Upload shared documents
        await self._upload_shared_documents(assistant_id, on_progress)

        # Step 3: Verify documents are indexed
        await self._verify_documents_indexed(assistant_id, on_progress)

        # Step 4: Store mapping in Supabase
        await self._store_user_assistant(user_id, assistant_id)

        return assistant_id

    async def _upload_shared_documents(
        self, assistant_id: str, on_progress: ProgressCallback = None
    ):
        """Upload all shared hackathon documents to an assistant."""
        client = self._get_client()
        total = len(SHARED_DOCUMENTS)

        for i, doc_name in enumerate(SHARED_DOCUMENTS, 1):
            doc_path = SHARED_DOCS_DIR / doc_name

            if not doc_path.exists():
                logger.warning(f"Shared doc not found: {doc_path}")
                continue

            if on_progress:
                await on_progress(
                    "uploading_docs",
                    f"Loading knowledge base... ({i}/{total})",
                    i, total,
                )

            try:
                logger.info(f"Uploading {doc_name} to assistant {assistant_id}")

                with open(doc_path, "rb") as f:
                    resp = await client.post(
                        f"{self.settings.backboard_base_url}/assistants/{assistant_id}/documents",
                        headers={"X-API-Key": self.settings.backboard_api_key},
                        files={"file": (doc_name, f, "application/octet-stream")}
                    )
                resp.raise_for_status()
                doc_data = resp.json()
                logger.info(f"Uploaded {doc_name}: {doc_data.get('document_id')}")

                # Small delay to avoid rate limiting
                await asyncio.sleep(0.3)

            except Exception as e:
                logger.error(f"Failed to upload {doc_name}: {e}")

    async def _verify_documents_indexed(
        self, assistant_id: str, on_progress: ProgressCallback = None
    ) -> bool:
        """Poll until all docs are indexed (max 90s)."""
        client = self._get_client()

        if on_progress:
            await on_progress("verifying", "Verifying document indexing...", 0, 0)

        for attempt in range(18):  # 18 × 5s = 90s max
            try:
                resp = await client.get(
                    f"{self.settings.backboard_base_url}/assistants/{assistant_id}/documents",
                    headers=self._headers,
                )
                resp.raise_for_status()
                docs = resp.json()

                if not isinstance(docs, list):
                    docs = docs.get("documents", [])

                total = len(docs)
                indexed = sum(1 for d in docs if d.get("status") == "indexed")

                if on_progress:
                    await on_progress(
                        "verifying",
                        f"Indexing documents ({indexed}/{total})...",
                        indexed, total,
                    )

                logger.debug(f"Doc indexing: {indexed}/{total}")

                if total > 0 and indexed == total:
                    logger.info(f"All {total} documents indexed for assistant {assistant_id}")
                    return True

            except Exception as e:
                logger.warning(f"Error checking doc status: {e}")

            await asyncio.sleep(5)

        logger.warning(f"Timed out waiting for doc indexing on assistant {assistant_id}")
        return False

    async def _store_user_assistant(self, user_id: str, assistant_id: str):
        """Store user -> assistant mapping in Supabase (upsert to avoid 409)."""
        client = self._get_client()

        try:
            resp = await client.post(
                f"{self.settings.supabase_url}/rest/v1/user_assistants",
                headers={
                    **self._supabase_headers,
                    "Prefer": "resolution=merge-duplicates,return=representation",
                },
                json={"user_id": user_id, "assistant_id": assistant_id}
            )
            resp.raise_for_status()
            logger.info(f"Stored assistant mapping: {user_id} -> {assistant_id}")
        except Exception as e:
            logger.error(f"Failed to store assistant mapping: {e}")
            raise

    async def get_or_create_assistant(
        self,
        user_id: str,
        user_name: Optional[str] = None,
        on_progress: ProgressCallback = None,
    ) -> str:
        """Get existing assistant or create a new one for user.

        Uses a per-user lock to prevent concurrent requests from
        creating duplicate assistants on first login.
        """
        # Fast path: already provisioned
        assistant_id = await self.get_user_assistant(user_id)
        if assistant_id:
            return assistant_id

        # Slow path: acquire lock so only one request provisions
        async with self._provision_locks[user_id]:
            # Re-check after acquiring lock (another request may have finished)
            assistant_id = await self.get_user_assistant(user_id)
            if assistant_id:
                return assistant_id

            return await self.create_assistant_for_user(
                user_id, user_name, on_progress=on_progress
            )

    async def delete_user_assistant(self, user_id: str) -> bool:
        """Delete a user's assistant (cleanup)."""
        client = self._get_client()

        assistant_id = await self.get_user_assistant(user_id)
        if not assistant_id:
            return False

        try:
            # Delete from Backboard
            resp = await client.delete(
                f"{self.settings.backboard_base_url}/assistants/{assistant_id}",
                headers=self._headers
            )
            resp.raise_for_status()

            # Delete from Supabase
            resp = await client.delete(
                f"{self.settings.supabase_url}/rest/v1/user_assistants",
                headers=self._supabase_headers,
                params={"user_id": f"eq.{user_id}"}
            )
            resp.raise_for_status()

            logger.info(f"Deleted assistant {assistant_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete assistant: {e}")
            return False

    async def aclose(self):
        """Cleanup HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_service: Optional[UserAssistantService] = None


def get_user_assistant_service() -> UserAssistantService:
    global _service
    if _service is None:
        _service = UserAssistantService()
    return _service
