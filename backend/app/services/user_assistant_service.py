"""
User Assistant Service - Creates and manages per-user Backboard assistants.

Each user gets their own assistant with:
1. Shared hackathon documents (uploaded on creation)
2. Isolated memories
3. Thread-level personal documents
"""

import asyncio
import httpx
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger

from app.config import get_settings
from app.assistant_template import (
    SYSTEM_PROMPT,
    SHARED_DOCUMENTS,
    SHARED_DOCS_DIR,
    ASSISTANT_CONFIG,
)


class UserAssistantService:
    """
    Manages per-user Backboard assistants.

    Flow:
    1. User signs up → create_assistant_for_user()
    2. Creates new Backboard assistant with system prompt
    3. Uploads all shared docs to the assistant
    4. Stores assistant_id in Supabase user_assistants table
    """

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None

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
        user_name: Optional[str] = None
    ) -> str:
        """
        Create a new Backboard assistant for a user.

        1. Creates assistant with system prompt
        2. Uploads shared documents
        3. Stores mapping in Supabase

        Returns: assistant_id
        """
        client = self._get_client()

        # Check if user already has an assistant
        existing = await self.get_user_assistant(user_id)
        if existing:
            logger.info(f"User {user_id} already has assistant {existing}")
            return existing

        # Create assistant
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

        # Upload shared documents
        await self._upload_shared_documents(assistant_id)

        # Store mapping in Supabase
        await self._store_user_assistant(user_id, assistant_id)

        return assistant_id

    async def _upload_shared_documents(self, assistant_id: str):
        """Upload all shared hackathon documents to an assistant."""
        client = self._get_client()

        for doc_name in SHARED_DOCUMENTS:
            doc_path = SHARED_DOCS_DIR / doc_name

            if not doc_path.exists():
                logger.warning(f"Shared doc not found: {doc_path}")
                continue

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
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to upload {doc_name}: {e}")

    async def _store_user_assistant(self, user_id: str, assistant_id: str):
        """Store user -> assistant mapping in Supabase."""
        client = self._get_client()

        try:
            resp = await client.post(
                f"{self.settings.supabase_url}/rest/v1/user_assistants",
                headers=self._supabase_headers,
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
        user_name: Optional[str] = None
    ) -> str:
        """Get existing assistant or create a new one for user."""
        assistant_id = await self.get_user_assistant(user_id)

        if assistant_id:
            return assistant_id

        return await self.create_assistant_for_user(user_id, user_name)

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
