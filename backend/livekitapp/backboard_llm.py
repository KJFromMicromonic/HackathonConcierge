"""
Backboard.io LLM plugin for LiveKit Agents.

Implements LiveKit's llm.LLM / llm.LLMStream interface to integrate
Backboard's thread-based conversation API (with memory and RAG)
into a LiveKit Agents voice pipeline.

Backboard manages its own conversation history via thread_id,
so we extract only the latest user message from ChatContext and
let Backboard handle the rest.

Frame Flow (LiveKit Agents pipeline):
  Audio → STT → SpeechEvent → AgentSession → ChatContext
    → BackboardLLM.chat() → BackboardLLMStream._run()
    → ChatChunk tokens → TTS → Audio
"""

import json
import uuid
from typing import Any, Optional

import httpx
from loguru import logger

from livekit.agents import llm
from livekit.agents.llm import (
    ChatChunk,
    ChatContext,
    ChoiceDelta,
    CompletionUsage,
    Tool,
)

try:
    from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions, NOT_GIVEN, NotGivenOr
except ImportError:
    # Fallback for different livekit-agents versions
    from livekit.agents import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions, NOT_GIVEN, NotGivenOr

from .session_store import SessionStore


class BackboardLLM(llm.LLM):
    """
    LiveKit Agents LLM plugin that routes inference through Backboard.io.

    Backboard provides:
    - Persistent memory across conversations
    - RAG over uploaded documents
    - Thread-based context management
    - Configurable LLM provider/model backend

    Usage:
        session = AgentSession(
            stt=deepgram.STT(),
            llm=BackboardLLM(
                api_key="...",
                base_url="https://app.backboard.io/api",
                user_id="user-123",
            ),
            tts=cartesia.TTS(),
        )
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://app.backboard.io/api",
        user_id: str = "default",
        assistant_id: Optional[str] = None,
        llm_provider: str = "openai",
        model_name: str = "gpt-4o-mini",
        session_store: Optional[SessionStore] = None,
    ) -> None:
        super().__init__()
        self._api_key = api_key
        self._base_url = base_url
        self._user_id = user_id
        self._assistant_id = assistant_id
        self._llm_provider = llm_provider
        self._model_name = model_name
        self._session_store = session_store or SessionStore(
            api_key=api_key,
            base_url=base_url,
            assistant_id=assistant_id or "",
        )
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def provider(self) -> str:
        return "backboard"

    def set_user_id(self, user_id: str) -> None:
        """Set the current user ID for thread management."""
        self._user_id = user_id

    def set_assistant_id(self, assistant_id: str) -> None:
        """Set the assistant ID (for per-user assistants)."""
        self._assistant_id = assistant_id
        self._session_store.set_assistant_id(assistant_id)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60)
        return self._client

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list[Tool] | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls: NotGivenOr[bool] = NOT_GIVEN,
        tool_choice: NotGivenOr[llm.ToolChoice] = NOT_GIVEN,
        extra_kwargs: NotGivenOr[dict[str, Any]] = NOT_GIVEN,
    ) -> "BackboardLLMStream":
        return BackboardLLMStream(
            llm=self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
            client=self._get_client(),
            api_key=self._api_key,
            base_url=self._base_url,
            user_id=self._user_id,
            assistant_id=self._assistant_id,
            llm_provider=self._llm_provider,
            model_name=self._model_name,
            session_store=self._session_store,
        )

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


class BackboardLLMStream(llm.LLMStream):
    """
    Streaming response from Backboard API.

    Parses Backboard's SSE format and pushes ChatChunk objects
    to the LiveKit Agents pipeline via self._event_ch.
    """

    def __init__(
        self,
        *,
        llm: BackboardLLM,
        chat_ctx: ChatContext,
        tools: list[Tool],
        conn_options: APIConnectOptions,
        client: httpx.AsyncClient,
        api_key: str,
        base_url: str,
        user_id: str,
        assistant_id: Optional[str],
        llm_provider: str,
        model_name: str,
        session_store: SessionStore,
    ) -> None:
        super().__init__(llm, chat_ctx=chat_ctx, tools=tools, conn_options=conn_options)
        self._client = client
        self._api_key = api_key
        self._base_url = base_url
        self._user_id = user_id
        self._assistant_id = assistant_id
        self._llm_provider = llm_provider
        self._model_name = model_name
        self._session_store = session_store

    def _extract_user_message(self) -> str:
        """
        Extract the latest user message from ChatContext.

        Backboard manages its own conversation history via thread_id,
        so we only need the most recent user message. Falls back to
        developer/system instructions (e.g. from generate_reply()).
        """
        for msg in reversed(self._chat_ctx.messages()):
            if msg.role == "user" and msg.text_content:
                return msg.text_content
        # Fallback: look for developer/system instructions
        # (used by generate_reply(instructions=...))
        for msg in reversed(self._chat_ctx.messages()):
            if msg.role in ("developer", "system") and msg.text_content:
                return msg.text_content
        return ""

    async def _run(self) -> None:
        """
        Stream a response from the Backboard API and push ChatChunks.

        1. Extract latest user message from ChatContext
        2. Get/create thread for this user via SessionStore
        3. Call Backboard streaming API
        4. Parse SSE events and push ChatChunk objects
        """
        user_message = self._extract_user_message()
        if not user_message:
            logger.warning("[BackboardLLM] No user message found in ChatContext")
            self._event_ch.send_nowait(
                ChatChunk(
                    id=str(uuid.uuid4()),
                    delta=ChoiceDelta(
                        role="assistant",
                        content="I didn't catch that. Could you please repeat?",
                    ),
                )
            )
            return

        # Get or create thread for this user
        thread_id = await self._session_store.get_or_create_thread(self._user_id)
        logger.debug(f"[BackboardLLM] Using thread {thread_id} for user {self._user_id}")

        request_id = str(uuid.uuid4())
        total_tokens = 0

        try:
            async with self._client.stream(
                "POST",
                f"{self._base_url}/threads/{thread_id}/messages",
                headers={
                    "X-API-Key": self._api_key,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "content": user_message,
                    "llm_provider": self._llm_provider,
                    "model_name": self._model_name,
                    "stream": "true",
                    "memory": "auto",
                },
            ) as response:
                response.raise_for_status()

                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk

                    # Parse SSE events (double newline delimited)
                    while "\n\n" in buffer:
                        event, buffer = buffer.split("\n\n", 1)

                        for line in event.split("\n"):
                            if not line.startswith("data: "):
                                continue

                            data = line[6:]
                            if data == "[DONE]":
                                return

                            try:
                                parsed = json.loads(data)
                            except json.JSONDecodeError:
                                continue

                            chunk_type = parsed.get("type")

                            if chunk_type == "content_streaming":
                                content = parsed.get("content")
                                if content:
                                    total_tokens += 1  # approximate token count
                                    self._event_ch.send_nowait(
                                        ChatChunk(
                                            id=request_id,
                                            delta=ChoiceDelta(
                                                role="assistant",
                                                content=content,
                                            ),
                                        )
                                    )

                            elif chunk_type == "message_complete":
                                # Push final usage metrics
                                self._event_ch.send_nowait(
                                    ChatChunk(
                                        id=request_id,
                                        usage=CompletionUsage(
                                            completion_tokens=total_tokens,
                                            prompt_tokens=0,
                                            total_tokens=total_tokens,
                                        ),
                                    )
                                )
                                return

        except httpx.TimeoutException as e:
            logger.error(f"[BackboardLLM] Timeout: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[BackboardLLM] HTTP {e.response.status_code}: {e}"
            )
            raise
        except Exception as e:
            logger.error(f"[BackboardLLM] Stream error: {e}")
            raise
