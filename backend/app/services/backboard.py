import asyncio
from typing import Optional
import uuid
import httpx

from app.config import get_settings


class BackboardService:
    """
    Backboard.io integration for Memory, RAG, and Conversation Threads.

    Uses direct HTTP calls to avoid SDK parsing issues.
    """

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.backboard_api_key
        self.base_url = self.settings.backboard_base_url
        self._assistant_id: Optional[uuid.UUID] = None
        self._client = httpx.Client(timeout=60)

    @property
    def headers(self) -> dict:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    async def initialize(self, assistant_id: Optional[str] = None):
        """Initialize with an existing assistant ID."""
        if assistant_id:
            self._assistant_id = uuid.UUID(assistant_id)
            return
        raise ValueError("assistant_id is required - create one via Backboard dashboard")

    @property
    def assistant_id(self) -> uuid.UUID:
        if not self._assistant_id:
            raise RuntimeError("BackboardService not initialized. Call initialize() first.")
        return self._assistant_id

    async def create_thread(self, user_id: str) -> str:
        """Create a new conversation thread."""
        loop = asyncio.get_event_loop()

        def _create():
            resp = self._client.post(
                f"{self.base_url}/assistants/{self.assistant_id}/threads",
                headers=self.headers,
                json={}
            )
            resp.raise_for_status()
            return resp.json()

        data = await loop.run_in_executor(None, _create)
        return data["thread_id"]

    async def query(
        self,
        user_id: str,
        thread_id: str,
        message: str,
        use_memory: bool = True
    ) -> str:
        """Send a message and get a response."""
        loop = asyncio.get_event_loop()

        def _query():
            # Use form data as the SDK does
            resp = self._client.post(
                f"{self.base_url}/threads/{thread_id}/messages",
                headers={"X-API-Key": self.api_key},
                data={
                    "content": message,
                    "llm_provider": self.settings.backboard_llm_provider,
                    "model_name": self.settings.backboard_model_name,
                    "stream": "false"
                }
            )
            resp.raise_for_status()
            return resp.json()

        data = await loop.run_in_executor(None, _query)

        # Extract content from response - handle various response structures
        if "content" in data:
            return data["content"]
        elif "message" in data and isinstance(data["message"], dict):
            return data["message"].get("content", "")
        elif "messages" in data and len(data["messages"]) > 0:
            return data["messages"][-1].get("content", "")
        elif "response" in data:
            return data["response"]
        else:
            # Return raw data for debugging
            return str(data)

    async def store_memory(self, content: str, metadata: Optional[dict] = None) -> str:
        """Store a fact in persistent memory."""
        loop = asyncio.get_event_loop()

        def _store():
            resp = self._client.post(
                f"{self.base_url}/assistants/{self.assistant_id}/memories",
                headers=self.headers,
                json={"content": content, "metadata": metadata or {}}
            )
            resp.raise_for_status()
            return resp.json()

        data = await loop.run_in_executor(None, _store)
        return data.get("memory_id", "")

    async def close(self):
        """Clean up."""
        self._client.close()
