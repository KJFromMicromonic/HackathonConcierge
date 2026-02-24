"""
Backboard.io LLM service for chat mode.

Provides streaming and non-streaming responses via the Backboard API
with persistent memory and RAG support.
"""

import json
import httpx
from typing import AsyncGenerator, Optional

from loguru import logger

from app.config import get_settings
from app.services.supabase_session_store import get_supabase_session_store


def get_session_store():
    return get_supabase_session_store()


class BackboardLLMService:
    """
    LLM service using Backboard.io for chat-mode conversations.

    Handles:
    - Streaming responses via SSE
    - Memory and RAG via Backboard API
    - Thread-based context management
    """

    def __init__(
        self,
        *,
        mode: str = "chat",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        settings = get_settings()
        self._api_key = api_key or settings.backboard_api_key
        self._base_url = base_url or settings.backboard_base_url
        self._mode = mode

        # Select model based on mode
        if llm_provider and model:
            self._llm_provider = llm_provider
            self._model = model
        elif mode == "voice":
            self._llm_provider = settings.voice_llm_provider
            self._model = settings.voice_model_name
            logger.info(f"Voice mode using: {self._llm_provider}/{self._model}")
        else:
            self._llm_provider = settings.chat_llm_provider
            self._model = settings.chat_model_name
            logger.info(f"Chat mode using: {self._llm_provider}/{self._model}")

        self._client: Optional[httpx.AsyncClient] = None
        self._session_store = get_session_store()

        self._current_user_id: Optional[str] = None

    def set_user_id(self, user_id: str):
        """Set the current user ID for thread management."""
        self._current_user_id = user_id
        logger.debug(f"BackboardLLMService: Set user_id to {user_id}")

    @property
    def headers(self) -> dict:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60)
        return self._client

    async def _stream_message(
        self,
        thread_id: str,
        content: str,
        *,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a message response from Backboard API.

        Args:
            thread_id: Backboard thread ID
            content: User message content
            llm_provider: Optional per-call override (e.g. "anthropic")
            model: Optional per-call override (e.g. "claude-sonnet-4-5-20250929")

        Yields:
            Token strings as they arrive
        """
        client = await self._get_client()

        provider = llm_provider or self._llm_provider
        model_name = model or self._model

        async with client.stream(
            "POST",
            f"{self._base_url}/threads/{thread_id}/messages",
            headers=self.headers,
            data={
                "content": content,
                "llm_provider": provider,
                "model_name": model_name,
                "stream": "true",
                "memory": "auto"
            }
        ) as response:
            response.raise_for_status()

            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk

                while "\n\n" in buffer:
                    event, buffer = buffer.split("\n\n", 1)

                    for line in event.split("\n"):
                        if line.startswith("data: "):
                            data = line[6:]

                            if data == "[DONE]":
                                return

                            try:
                                parsed = json.loads(data)

                                chunk_type = parsed.get("type")
                                if chunk_type == "content_streaming":
                                    if parsed.get("content"):
                                        yield parsed["content"]
                                elif chunk_type == "message_complete":
                                    return
                            except json.JSONDecodeError:
                                pass

    async def get_response(self, user_message: str) -> str:
        """
        Get a complete response (non-streaming).

        Args:
            user_message: The user's message text

        Returns:
            The assistant's response text
        """
        if not user_message.strip():
            return "I didn't catch that. Could you please repeat?"

        user_id = self._current_user_id or "default_user"
        thread_id = await self._session_store.get_or_create_thread_async(user_id)

        full_response = ""
        try:
            async for token in self._stream_message(thread_id, user_message):
                full_response += token
        except Exception as e:
            logger.error(f"[Backboard] Error: {e}")
            return f"I'm sorry, I encountered an error: {str(e)}"

        response = full_response.strip()
        if response.startswith(user_message):
            response = response[len(user_message):].strip()

        return response or "I'm not sure how to respond to that."

    async def get_response_stream(
        self,
        user_message: str,
        *,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens (for chat mode with streaming).

        Args:
            user_message: The user's message text
            llm_provider: Optional per-call provider override
            model: Optional per-call model override

        Yields:
            Response tokens as they arrive
        """
        if not user_message.strip():
            yield "I didn't catch that. Could you please repeat?"
            return

        user_id = self._current_user_id or "default_user"
        thread_id = await self._session_store.get_or_create_thread_async(user_id)

        try:
            async for token in self._stream_message(
                thread_id, user_message, llm_provider=llm_provider, model=model
            ):
                yield token
        except Exception as e:
            logger.error(f"[Backboard] Stream error: {e}")
            yield f"I'm sorry, I encountered an error: {str(e)}"

    async def cleanup(self):
        """Clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.debug("BackboardLLMService cleaned up")
