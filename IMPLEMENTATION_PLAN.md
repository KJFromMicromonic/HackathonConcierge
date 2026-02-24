# AURA Implementation Plan

## Hackathon Concierge - Pipecat + Backboard + Speechmatics

**Project:** AURA (Activate Your Voice)
**Goal:** ChatGPT/Claude-style application with Chat Mode + Voice Mode, RAG for Partner SDK docs
**Architecture:** Pipecat pipeline with custom BackboardLLMService

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Current State Assessment](#current-state-assessment)
3. [Implementation Phases](#implementation-phases)
4. [Phase 1: Pipecat LLM Service](#phase-1-pipecat-llm-service)
5. [Phase 2: Voice Pipeline Integration](#phase-2-voice-pipeline-integration)
6. [Phase 3: Chat Mode & Thread Management](#phase-3-chat-mode--thread-management)
7. [Phase 4: Frontend Updates](#phase-4-frontend-updates)
8. [Phase 5: RAG Setup](#phase-5-rag-setup)
9. [Phase 6: Polish & Deploy](#phase-6-polish--deploy)
10. [API Specification](#api-specification)
11. [Testing Checklist](#testing-checklist)

---

## Architecture Overview

### Pipecat Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VOICE MODE PIPELINE                             │
│                                  (Pipecat)                                   │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐     ┌─────────────────────────────────────────────────┐
    │   BROWSER    │     │              PIPECAT PIPELINE                    │
    │              │     │                                                  │
    │  Microphone  │═════│══▶ WebSocketTransport.input()                   │
    │      ↓       │     │              │                                  │
    │  Audio Bytes │     │              ▼                                  │
    │              │     │    ┌─────────────────────┐                      │
    │              │     │    │  Speechmatics STT   │  ◀── pipecat-ai      │
    │              │     │    │  (Audio → Text)     │      [speechmatics]  │
    │              │     │    └──────────┬──────────┘                      │
    │              │     │               │ TextFrame                       │
    │              │     │               ▼                                  │
    │              │     │    ┌─────────────────────┐                      │
    │              │     │    │ BackboardLLMService │  ◀── Custom Service  │
    │              │     │    │  • Memory           │                      │
    │              │     │    │  • RAG              │                      │
    │              │     │    │  • Thread Context   │                      │
    │              │     │    └──────────┬──────────┘                      │
    │              │     │               │ TextFrame                       │
    │              │     │               ▼                                  │
    │              │     │    ┌─────────────────────┐                      │
    │              │     │    │  Speechmatics TTS   │  ◀── pipecat-ai      │
    │              │     │    │  (Text → Audio)     │      [speechmatics]  │
    │              │     │    └──────────┬──────────┘                      │
    │              │     │               │                                  │
    │   Speaker    │◀════│═══ WebSocketTransport.output() ◀────────────────│
    │      ↑       │     │                                                  │
    │  Audio Bytes │     └─────────────────────────────────────────────────┘
    └──────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                               CHAT MODE                                      │
│                           (Direct REST/WebSocket)                            │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐     ┌─────────────────────────────────────────────────┐
    │   BROWSER    │     │                  BACKEND                         │
    │              │     │                                                  │
    │  Text Input  │─────│──▶ WebSocket "text_in"                          │
    │              │     │              │                                  │
    │              │     │              ▼                                  │
    │              │     │    ┌─────────────────────┐                      │
    │              │     │    │ BackboardLLMService │                      │
    │              │     │    │  (Same service,     │                      │
    │              │     │    │   direct call)      │                      │
    │              │     │    └──────────┬──────────┘                      │
    │              │     │               │                                  │
    │  Text Output │◀────│───  WebSocket "response"  ◀─────────────────────│
    └──────────────┘     └─────────────────────────────────────────────────┘
```

### Dual Mode Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AURA BACKEND                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   WebSocket /ws/{user_id}                                                   │
│   ├── "text_in"  ──────────────▶  BackboardLLMService.get_response()       │
│   │                                        │                                │
│   │                                        ▼                                │
│   │                               "response" ◀─────────────────────────────│
│   │                                                                         │
│   └── "audio_in" ──────────────▶  Pipecat Pipeline                         │
│                                   ┌─────────────────┐                      │
│                                   │ STT → LLM → TTS │                      │
│                                   └────────┬────────┘                      │
│                                            │                                │
│                               "audio_out" ◀┘                               │
│                                                                              │
│   REST Endpoints                                                            │
│   ├── GET  /threads         ──▶  List threads from Backboard               │
│   ├── POST /threads         ──▶  Create new thread                         │
│   ├── GET  /threads/{id}    ──▶  Get thread messages                       │
│   └── DELETE /threads/{id}  ──▶  Delete thread                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Current State Assessment

### What's DONE ✅

| Component | File | Status |
|-----------|------|--------|
| Pipecat Pipeline Definition | `pipeline.py` | ✅ Defined but not used |
| BackboardLLMService | `backboard_llm.py` | ✅ Works for text, needs Pipecat interface |
| Session Store | `session_store.py` | ✅ Thread management working |
| WebSocket Handler | `main.py` | ✅ Text mode works, voice is TODO |
| Frontend Voice UI | `VoiceInterface.tsx` | ✅ Recording works |
| Frontend WebSocket | `useWebSocket.ts` | ✅ Connection works |
| Docker Setup | `docker-compose.yml` | ✅ Complete |

### What's MISSING ❌

| Component | Priority | Effort |
|-----------|----------|--------|
| Pipecat LLM interface on BackboardLLMService | HIGH | 2 hours |
| Wire Pipecat pipeline into main.py | HIGH | 2 hours |
| Thread list REST endpoints | HIGH | 1 hour |
| Thread sidebar UI | HIGH | 2 hours |
| Chat input component | MEDIUM | 1 hour |
| Mode toggle | MEDIUM | 1 hour |
| RAG document upload | HIGH | 1 hour |

---

## Implementation Phases

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Phase 1: Pipecat LLM Service    │████████████████│  ~2 hours            │
│  - Implement Pipecat interface   │                │                      │
│  - Frame handling                │                │                      │
├─────────────────────────────────┼────────────────┼──────────────────────┤
│  Phase 2: Voice Pipeline         │████████████████│  ~3 hours            │
│  - Wire pipeline into main.py   │                │                      │
│  - Handle audio WebSocket flow   │                │                      │
├─────────────────────────────────┼────────────────┼──────────────────────┤
│  Phase 3: Chat + Threads         │████████████│     ~3 hours            │
│  - REST endpoints                │                │                      │
│  - Thread switching              │                │                      │
├─────────────────────────────────┼────────────────┼──────────────────────┤
│  Phase 4: Frontend Updates       │████████████│     ~3 hours            │
│  - Sidebar component             │                │                      │
│  - Mode toggle                   │                │                      │
│  - Chat input                    │                │                      │
├─────────────────────────────────┼────────────────┼──────────────────────┤
│  Phase 5: RAG Setup              │████████│         ~1 hour             │
│  - Upload SDK docs               │                │                      │
├─────────────────────────────────┼────────────────┼──────────────────────┤
│  Phase 6: Polish                 │████████│         ~2 hours            │
│  - Error handling                │                │                      │
│  - Testing                       │                │                      │
└──────────────────────────────────────────────────────────────────────────┘

TOTAL ESTIMATED TIME: ~14 hours
```

---

## Phase 1: Pipecat LLM Service

### 1.1 Understanding Pipecat Frame Flow

Pipecat uses a frame-based architecture:
- **Input Frames**: `AudioRawFrame`, `TextFrame`, `TranscriptionFrame`
- **Output Frames**: `TextFrame`, `LLMFullResponseStartFrame`, `LLMFullResponseEndFrame`

The LLM service receives transcribed text and outputs response text.

### 1.2 Update BackboardLLMService for Pipecat

**File:** `backend/app/services/backboard_llm.py`

```python
"""
Backboard.io LLM service for Pipecat pipeline.

Implements Pipecat's LLM service interface for:
- Conversation with persistent memory
- RAG over uploaded documents
- Thread-based context management
"""

import json
import httpx
from typing import AsyncGenerator, Optional, List

from pipecat.frames.frames import (
    Frame,
    TextFrame,
    LLMFullResponseStartFrame,
    LLMFullResponseEndFrame,
    ErrorFrame
)
from pipecat.services.ai_services import LLMService
from pipecat.processors.frame_processor import FrameDirection

from app.config import get_settings
from app.services.session_store import get_session_store


class BackboardLLMService(LLMService):
    """
    Pipecat-compatible LLM service using Backboard.io.

    Handles:
    - Text frames from STT
    - Streaming responses to TTS
    - Memory and RAG via Backboard
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        assistant_id: Optional[str] = None,
        llm_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)

        settings = get_settings()
        self.api_key = api_key or settings.backboard_api_key
        self.base_url = base_url or settings.backboard_base_url
        self.assistant_id = assistant_id or settings.backboard_assistant_id
        self.llm_provider = llm_provider or settings.backboard_llm_provider
        self.model_name = model_name or settings.backboard_model_name

        self._client = httpx.AsyncClient(timeout=60)
        self._session_store = get_session_store()

        # Current user context (set per connection)
        self._current_user_id: Optional[str] = None

        # Accumulated text from transcription
        self._accumulated_text: str = ""

    def set_user_id(self, user_id: str):
        """Set the current user ID for thread management."""
        self._current_user_id = user_id

    @property
    def headers(self) -> dict:
        return {"X-API-Key": self.api_key}

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """
        Process incoming frames from the pipeline.

        Handles TextFrame from STT and generates response TextFrames for TTS.
        """
        await super().process_frame(frame, direction)

        if isinstance(frame, TextFrame):
            # Got transcribed text from STT
            text = frame.text.strip()

            if not text:
                return

            # Log the input
            user_id = self._current_user_id or "default"
            print(f"[Backboard][{user_id}] Input: {text}")

            # Signal start of response
            await self.push_frame(LLMFullResponseStartFrame())

            try:
                # Get thread for this user
                thread_id = self._session_store.get_or_create_thread(
                    self._current_user_id or "default_user"
                )

                # Stream response from Backboard
                full_response = ""
                async for token in self._stream_message(thread_id, text):
                    full_response += token
                    # Push each token as a TextFrame for TTS
                    await self.push_frame(TextFrame(text=token))

                print(f"[Backboard][{user_id}] Response: {full_response[:100]}...")

            except Exception as e:
                print(f"[Backboard] Error: {e}")
                error_msg = "I'm sorry, I encountered an error processing your request."
                await self.push_frame(TextFrame(text=error_msg))

            # Signal end of response
            await self.push_frame(LLMFullResponseEndFrame())

        else:
            # Pass through other frames
            await self.push_frame(frame, direction)

    async def _stream_message(
        self,
        thread_id: str,
        content: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream a message response from Backboard.

        Args:
            thread_id: Backboard thread ID
            content: User message content

        Yields:
            Token strings as they arrive
        """
        async with self._client.stream(
            "POST",
            f"{self.base_url}/threads/{thread_id}/messages",
            headers=self.headers,
            data={
                "content": content,
                "llm_provider": self.llm_provider,
                "model_name": self.model_name,
                "stream": "true",
                "memory": "auto"  # Enable memory
            }
        ) as response:
            response.raise_for_status()

            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk

                # Parse SSE events
                while "\n\n" in buffer:
                    event, buffer = buffer.split("\n\n", 1)

                    for line in event.split("\n"):
                        if line.startswith("data: "):
                            data = line[6:]

                            if data == "[DONE]":
                                return

                            try:
                                parsed = json.loads(data)

                                # Handle different response formats
                                if "delta" in parsed:
                                    yield parsed["delta"]
                                elif "content" in parsed:
                                    yield parsed["content"]
                                elif "text" in parsed:
                                    yield parsed["text"]
                            except json.JSONDecodeError:
                                if data.strip():
                                    yield data

    # ==================== NON-PIPECAT METHODS ====================
    # These are used for Chat Mode (direct calls without pipeline)

    async def get_response(self, user_message: str) -> str:
        """
        Get a complete response (non-streaming, for chat mode).

        Args:
            user_message: The user's message text

        Returns:
            The assistant's response text
        """
        if not user_message.strip():
            return "I didn't catch that. Could you please repeat?"

        user_id = self._current_user_id or "default_user"
        thread_id = self._session_store.get_or_create_thread(user_id)

        full_response = ""
        try:
            async for token in self._stream_message(thread_id, user_message):
                full_response += token
        except Exception as e:
            print(f"[Backboard] Error: {e}")
            return f"I'm sorry, I encountered an error: {str(e)}"

        return full_response.strip() or "I'm not sure how to respond to that."

    async def get_response_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        """
        Stream response tokens (for chat mode with streaming).

        Args:
            user_message: The user's message text

        Yields:
            Response tokens as they arrive
        """
        if not user_message.strip():
            yield "I didn't catch that. Could you please repeat?"
            return

        user_id = self._current_user_id or "default_user"
        thread_id = self._session_store.get_or_create_thread(user_id)

        try:
            async for token in self._stream_message(thread_id, user_message):
                yield token
        except Exception as e:
            print(f"[Backboard] Stream error: {e}")
            yield f"I'm sorry, I encountered an error: {str(e)}"

    async def cleanup(self):
        """Clean up resources."""
        await self._client.aclose()
```

---

## Phase 2: Voice Pipeline Integration

### 2.1 Update Pipeline Factory

**File:** `backend/app/pipeline.py`

```python
"""
Pipecat pipeline factory for voice conversation.
"""

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.aggregators.llm_response import LLMResponseAggregator
from pipecat.processors.aggregators.sentence import SentenceAggregator
from pipecat.services.speechmatics import SpeechmaticsSTTService, SpeechmaticsTTSService
from pipecat.transports.websocket.websocket_server import WebSocketServerTransport
from pipecat.vad.silero import SileroVADAnalyzer

from app.config import get_settings
from app.services.backboard_llm import BackboardLLMService


def create_voice_pipeline(
    transport: WebSocketServerTransport,
    user_id: str
) -> tuple[Pipeline, PipelineTask]:
    """
    Create a Pipecat pipeline for voice conversation.

    Pipeline flow:
    1. WebSocket input (audio from browser)
    2. VAD (Voice Activity Detection)
    3. Speechmatics STT (speech to text)
    4. BackboardLLM (with memory/RAG)
    5. Sentence aggregator (for natural TTS)
    6. Speechmatics TTS (text to speech)
    7. WebSocket output (audio to browser)

    Args:
        transport: WebSocket transport instance
        user_id: User identifier for session management

    Returns:
        Tuple of (Pipeline, PipelineTask)
    """
    settings = get_settings()

    # Voice Activity Detection
    vad = SileroVADAnalyzer()

    # Speechmatics STT (Speech-to-Text)
    stt = SpeechmaticsSTTService(
        api_key=settings.speechmatics_api_key,
        language="en"
    )

    # Backboard LLM (our custom service with memory/RAG)
    llm = BackboardLLMService()
    llm.set_user_id(user_id)

    # Aggregate LLM response for cleaner output
    llm_aggregator = LLMResponseAggregator()

    # Aggregate into sentences for natural TTS
    sentence_aggregator = SentenceAggregator()

    # Speechmatics TTS (Text-to-Speech)
    tts = SpeechmaticsTTSService(
        api_key=settings.speechmatics_api_key,
        voice="en-GB-female-1"
    )

    # Build pipeline
    pipeline = Pipeline([
        transport.input(),      # Audio from WebSocket
        vad,                    # Voice activity detection
        stt,                    # Speech to text
        llm,                    # Backboard LLM (with memory/RAG)
        llm_aggregator,         # Aggregate response
        sentence_aggregator,    # Split into sentences
        tts,                    # Text to speech
        transport.output()      # Audio to WebSocket
    ])

    # Create task with interruption support
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True
        )
    )

    return pipeline, task


def create_simple_pipeline(
    transport: WebSocketServerTransport,
    user_id: str
) -> tuple[Pipeline, PipelineTask]:
    """
    Simplified pipeline without VAD/aggregators (for testing).
    """
    settings = get_settings()

    stt = SpeechmaticsSTTService(
        api_key=settings.speechmatics_api_key,
        language="en"
    )

    llm = BackboardLLMService()
    llm.set_user_id(user_id)

    tts = SpeechmaticsTTSService(
        api_key=settings.speechmatics_api_key,
        voice="en-GB-female-1"
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        llm,
        tts,
        transport.output()
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True
        )
    )

    return pipeline, task
```

### 2.2 Update Main Application

**File:** `backend/app/main.py`

```python
"""
Hackathon Concierge Backend

Dual-mode voice AI:
- Chat Mode: Direct text via WebSocket
- Voice Mode: Pipecat pipeline with Speechmatics STT/TTS + Backboard LLM
"""

import asyncio
import json
import base64
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pipecat.transports.websocket.websocket_server import WebSocketServerParams
from pipecat.transports.websocket.fastapi_websocket import FastAPIWebsocketTransport

from app.config import get_settings
from app.services.backboard_llm import BackboardLLMService
from app.services.session_store import get_session_store
from app.pipeline import create_voice_pipeline

from backboard import BackboardClient


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print(f"🚀 Starting {settings.app_name}...")
    yield
    print("👋 Shutting down...")
    get_session_store().close()


app = FastAPI(
    title=settings.app_name,
    description="Voice-powered AI concierge with Backboard memory/RAG",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Backboard client for REST endpoints
backboard_client: Optional[BackboardClient] = None


def get_backboard_client() -> BackboardClient:
    global backboard_client
    if backboard_client is None:
        backboard_client = BackboardClient(api_key=settings.backboard_api_key)
    return backboard_client


# ==================== REST ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "status": "running",
        "modes": ["chat", "voice"],
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/threads")
async def list_threads():
    """List all conversation threads."""
    try:
        client = get_backboard_client()
        threads = await client.list_threads(limit=50)
        return {
            "threads": [
                {
                    "thread_id": str(t.thread_id),
                    "created_at": t.created_at.isoformat(),
                    "message_count": len(t.messages),
                    "preview": (
                        t.messages[-1].content[:50] + "..."
                        if t.messages and t.messages[-1].content
                        else "New conversation"
                    )
                }
                for t in threads
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/threads")
async def create_thread():
    """Create a new conversation thread."""
    try:
        client = get_backboard_client()
        thread = await client.create_thread(settings.backboard_assistant_id)
        return {
            "thread_id": str(thread.thread_id),
            "created_at": thread.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/threads/{thread_id}")
async def get_thread(thread_id: str):
    """Get a thread with all messages."""
    try:
        client = get_backboard_client()
        thread = await client.get_thread(thread_id)
        return {
            "thread_id": str(thread.thread_id),
            "created_at": thread.created_at.isoformat(),
            "messages": [
                {
                    "message_id": str(m.message_id),
                    "role": m.role.value,
                    "content": m.content,
                    "created_at": m.created_at.isoformat()
                }
                for m in thread.messages
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    """Delete a thread."""
    try:
        client = get_backboard_client()
        await client.delete_thread(thread_id)
        return {"status": "deleted", "thread_id": thread_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WEBSOCKET ENDPOINT ====================

async def send_json(websocket: WebSocket, msg_type: str, data):
    """Send a JSON message to the WebSocket client."""
    await websocket.send_json({"type": msg_type, "data": data})


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for conversation.

    Supports two modes:
    1. Chat Mode: {type: "text_in", text: "..."} → {type: "response", data: "..."}
    2. Voice Mode: {type: "audio_in", audio: "base64..."} → Pipecat pipeline

    Protocol:
    - "text_in"     → Direct text message (chat mode)
    - "audio_in"    → Audio for voice pipeline
    - "switch_thread" → Switch to different thread
    - "new_thread"  → Create new thread

    Server responses:
    - "status"      → Status updates
    - "transcript"  → Transcribed speech
    - "response"    → Text response
    - "audio_out"   → Audio response
    - "error"       → Error message
    - "thread_switched" / "thread_created" → Thread management
    """
    await websocket.accept()
    print(f"✅ User {user_id} connected")

    # Services for this connection
    llm_service = BackboardLLMService()
    llm_service.set_user_id(user_id)
    session_store = get_session_store()

    # Pipeline task (created on first audio)
    pipeline_task = None

    try:
        await send_json(websocket, "status", "connected")

        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            # ============ CHAT MODE: TEXT INPUT ============
            if msg_type == "text_in":
                text = message.get("text", "").strip()
                if not text:
                    continue

                print(f"💬 [{user_id}] Text: {text}")
                await send_json(websocket, "status", "thinking")

                # Get response from Backboard (direct call, no pipeline)
                response = await llm_service.get_response(text)
                print(f"🤖 [{user_id}] Response: {response[:100]}...")

                await send_json(websocket, "response", response)
                await send_json(websocket, "status", "connected")

            # ============ VOICE MODE: AUDIO INPUT ============
            elif msg_type == "audio_in":
                audio_base64 = message.get("audio", "")
                if not audio_base64:
                    continue

                print(f"🎤 [{user_id}] Received audio")

                # Create pipeline transport and task if not exists
                if pipeline_task is None:
                    try:
                        # Create FastAPI WebSocket transport for Pipecat
                        transport = FastAPIWebsocketTransport(
                            websocket=websocket,
                            params=WebSocketServerParams(
                                audio_in_enabled=True,
                                audio_out_enabled=True,
                                transcription_enabled=True
                            )
                        )

                        # Create pipeline
                        pipeline, pipeline_task = create_voice_pipeline(
                            transport=transport,
                            user_id=user_id
                        )

                        # Run pipeline in background
                        asyncio.create_task(pipeline_task.run())
                        print(f"🎙️ [{user_id}] Voice pipeline started")

                    except Exception as e:
                        print(f"❌ Pipeline error: {e}")
                        await send_json(websocket, "error", f"Voice pipeline error: {e}")
                        continue

                # Feed audio to pipeline
                try:
                    audio_bytes = base64.b64decode(audio_base64)
                    await pipeline_task.queue_frame(
                        AudioRawFrame(audio=audio_bytes, sample_rate=16000, num_channels=1)
                    )
                except Exception as e:
                    print(f"❌ Audio processing error: {e}")
                    await send_json(websocket, "error", str(e))

            # ============ THREAD MANAGEMENT ============
            elif msg_type == "switch_thread":
                thread_id = message.get("thread_id")
                if thread_id:
                    session_store.switch_thread(user_id, thread_id)
                    llm_service.set_user_id(user_id)  # Refresh service
                    await send_json(websocket, "thread_switched", thread_id)
                    print(f"🔄 [{user_id}] Switched to thread {thread_id}")

            elif msg_type == "new_thread":
                thread_id = await session_store.create_new_thread(user_id)
                llm_service.set_user_id(user_id)  # Refresh service
                await send_json(websocket, "thread_created", thread_id)
                print(f"✨ [{user_id}] Created new thread {thread_id}")

    except WebSocketDisconnect:
        print(f"👋 User {user_id} disconnected")
    except Exception as e:
        print(f"❌ Error for {user_id}: {e}")
        try:
            await send_json(websocket, "error", str(e))
        except:
            pass
    finally:
        # Cleanup
        if pipeline_task:
            await pipeline_task.cancel()
        await llm_service.cleanup()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2.3 Add Missing Import

Add to main.py:

```python
from pipecat.frames.frames import AudioRawFrame
```

---

## Phase 3: Chat Mode & Thread Management

### 3.1 Update Session Store

**File:** `backend/app/services/session_store.py`

```python
"""
Session store for managing user threads.
"""

from typing import Dict, Optional
from backboard import BackboardClient
from app.config import get_settings


class SessionStore:
    """
    Manages user sessions and thread associations.

    Thread lifecycle:
    1. User connects → get_or_create_thread()
    2. User switches thread → switch_thread()
    3. User creates new → create_new_thread()
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sessions: Dict[str, str] = {}  # user_id -> current_thread_id
            cls._instance._client: Optional[BackboardClient] = None
        return cls._instance

    @property
    def client(self) -> BackboardClient:
        if self._client is None:
            settings = get_settings()
            self._client = BackboardClient(api_key=settings.backboard_api_key)
        return self._client

    def get_or_create_thread(self, user_id: str) -> str:
        """Get current thread or create new one synchronously."""
        if user_id in self._sessions:
            return self._sessions[user_id]

        # Create new thread (blocking call wrapped)
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in async context, need to handle differently
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self._create_thread_async(user_id)
                    )
                    return future.result()
            else:
                return asyncio.run(self._create_thread_async(user_id))
        except Exception as e:
            print(f"Error creating thread: {e}")
            # Return a placeholder that will be replaced on first message
            return f"pending_{user_id}"

    async def _create_thread_async(self, user_id: str) -> str:
        """Create thread asynchronously."""
        settings = get_settings()
        thread = await self.client.create_thread(settings.backboard_assistant_id)
        thread_id = str(thread.thread_id)
        self._sessions[user_id] = thread_id
        return thread_id

    async def create_new_thread(self, user_id: str) -> str:
        """Create a new thread for user."""
        settings = get_settings()
        thread = await self.client.create_thread(settings.backboard_assistant_id)
        thread_id = str(thread.thread_id)
        self._sessions[user_id] = thread_id
        return thread_id

    def switch_thread(self, user_id: str, thread_id: str) -> str:
        """Switch user to a different thread."""
        self._sessions[user_id] = thread_id
        return thread_id

    def get_current_thread(self, user_id: str) -> Optional[str]:
        """Get user's current thread ID."""
        return self._sessions.get(user_id)

    def clear_session(self, user_id: str):
        """Clear user's current session."""
        if user_id in self._sessions:
            del self._sessions[user_id]

    def close(self):
        """Clean up resources."""
        if self._client:
            # Client cleanup if needed
            pass


# Singleton accessor
_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
```

---

## Phase 4: Frontend Updates

### 4.1 Thread Sidebar Component

**File:** `frontend/src/components/ThreadSidebar.tsx`

```tsx
import React, { useEffect, useState } from 'react';

interface Thread {
  thread_id: string;
  created_at: string;
  message_count: number;
  preview: string;
}

interface ThreadSidebarProps {
  currentThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onNewThread: () => void;
}

export const ThreadSidebar: React.FC<ThreadSidebarProps> = ({
  currentThreadId,
  onSelectThread,
  onNewThread
}) => {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchThreads = async () => {
    try {
      const baseUrl = import.meta.env.DEV ? 'http://localhost:8000' : '';
      const response = await fetch(`${baseUrl}/threads`);
      const data = await response.json();
      setThreads(data.threads || []);
    } catch (error) {
      console.error('Failed to fetch threads:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchThreads();
  }, []);

  // Refresh when a new thread is created
  useEffect(() => {
    if (currentThreadId) {
      fetchThreads();
    }
  }, [currentThreadId]);

  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="thread-sidebar">
      <div className="sidebar-header">
        <h2>Conversations</h2>
        <button className="new-thread-btn" onClick={onNewThread}>
          + New
        </button>
      </div>

      <div className="thread-list">
        {loading ? (
          <div className="loading-threads">Loading...</div>
        ) : threads.length === 0 ? (
          <div className="empty-threads">
            <p>No conversations yet</p>
            <p className="hint">Start chatting to create one!</p>
          </div>
        ) : (
          threads.map((thread) => (
            <div
              key={thread.thread_id}
              className={`thread-item ${thread.thread_id === currentThreadId ? 'active' : ''}`}
              onClick={() => onSelectThread(thread.thread_id)}
            >
              <div className="thread-preview">{thread.preview}</div>
              <div className="thread-meta">
                <span className="thread-date">{formatDate(thread.created_at)}</span>
                <span className="message-count">{thread.message_count} msgs</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
```

### 4.2 Mode Toggle Component

**File:** `frontend/src/components/ModeToggle.tsx`

```tsx
import React from 'react';

type Mode = 'chat' | 'voice';

interface ModeToggleProps {
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  disabled?: boolean;
}

export const ModeToggle: React.FC<ModeToggleProps> = ({
  mode,
  onModeChange,
  disabled = false
}) => {
  return (
    <div className="mode-toggle">
      <button
        className={`mode-btn ${mode === 'chat' ? 'active' : ''}`}
        onClick={() => onModeChange('chat')}
        disabled={disabled}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
        </svg>
        <span>Chat</span>
      </button>
      <button
        className={`mode-btn ${mode === 'voice' ? 'active' : ''}`}
        onClick={() => onModeChange('voice')}
        disabled={disabled}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
          <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
        </svg>
        <span>Voice</span>
      </button>
    </div>
  );
};
```

### 4.3 Chat Input Component

**File:** `frontend/src/components/ChatInput.tsx`

```tsx
import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = "Type a message..."
}) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [text]);

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (trimmed && !disabled) {
      onSendMessage(trimmed);
      setText('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="chat-input-container">
      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="chat-textarea"
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !text.trim()}
        className="send-button"
        aria-label="Send message"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
        </svg>
      </button>
    </div>
  );
};
```

### 4.4 Update App.tsx

**File:** `frontend/src/App.tsx`

```tsx
import React, { useState, useEffect, useCallback } from 'react';
import { ThreadSidebar } from './components/ThreadSidebar';
import { ConversationHistory } from './components/ConversationHistory';
import { ChatInput } from './components/ChatInput';
import { VoiceInterface } from './components/VoiceInterface';
import { ModeToggle } from './components/ModeToggle';
import { useWebSocket } from './hooks/useWebSocket';
import './styles/main.css';

type Mode = 'chat' | 'voice';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

function App() {
  // Persistent user ID
  const [userId] = useState(() => {
    const stored = localStorage.getItem('aura_user_id');
    if (stored) return stored;
    const newId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('aura_user_id', newId);
    return newId;
  });

  // UI State
  const [mode, setMode] = useState<Mode>('chat');
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 768);

  // WebSocket connection
  const {
    isConnected,
    status,
    sendAudio,
    sendText,
    lastTranscript,
    lastResponse,
    lastAudio,
    switchThread,
    createNewThread
  } = useWebSocket(userId);

  // Add user message to UI
  const addUserMessage = useCallback((content: string) => {
    const newMsg: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMsg]);
  }, []);

  // Handle assistant response
  useEffect(() => {
    if (lastResponse) {
      const newMsg: Message = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: lastResponse,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, newMsg]);
    }
  }, [lastResponse]);

  // Handle voice transcript
  useEffect(() => {
    if (lastTranscript) {
      addUserMessage(lastTranscript);
    }
  }, [lastTranscript, addUserMessage]);

  // Handle thread selection
  const handleSelectThread = async (threadId: string) => {
    setCurrentThreadId(threadId);
    switchThread(threadId);

    // Load thread messages
    try {
      const baseUrl = import.meta.env.DEV ? 'http://localhost:8000' : '';
      const response = await fetch(`${baseUrl}/threads/${threadId}`);
      const data = await response.json();

      setMessages(data.messages.map((m: any) => ({
        id: m.message_id,
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at)
      })));
    } catch (error) {
      console.error('Failed to load thread:', error);
    }
  };

  // Handle new thread
  const handleNewThread = async () => {
    const threadId = await createNewThread();
    if (threadId) {
      setCurrentThreadId(threadId);
      setMessages([]);
    }
  };

  // Handle text send (chat mode)
  const handleSendText = (text: string) => {
    addUserMessage(text);
    sendText(text);
  };

  // Handle audio send (voice mode)
  const handleSendAudio = async (audioBlob: Blob) => {
    await sendAudio(audioBlob);
  };

  // Responsive sidebar
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 768) {
        setSidebarOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isProcessing = status === 'thinking' || status === 'transcribing' || status === 'synthesizing';

  return (
    <div className={`app-container ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <ThreadSidebar
          currentThreadId={currentThreadId}
          onSelectThread={handleSelectThread}
          onNewThread={handleNewThread}
        />
      </aside>

      {/* Sidebar overlay for mobile */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <main className="main-content">
        {/* Header */}
        <header className="app-header">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle sidebar"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
              <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
            </svg>
          </button>

          <h1 className="logo">
            <span className="logo-text">AURA</span>
            <span className="logo-tagline">Voice AI Concierge</span>
          </h1>

          <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot"></span>
            <span className="status-text">
              {isConnected ? 'Connected' : 'Connecting...'}
            </span>
          </div>
        </header>

        {/* Conversation */}
        <div className="conversation-container">
          <ConversationHistory messages={messages} />
        </div>

        {/* Input Area */}
        <div className="input-area">
          <ModeToggle
            mode={mode}
            onModeChange={setMode}
            disabled={isProcessing}
          />

          {mode === 'chat' ? (
            <ChatInput
              onSendMessage={handleSendText}
              disabled={!isConnected || isProcessing}
              placeholder="Ask about Backboard, Speechmatics, or building voice AI..."
            />
          ) : (
            <VoiceInterface
              isConnected={isConnected}
              status={status}
              onSendAudio={handleSendAudio}
              onSendText={handleSendText}
              lastAudio={lastAudio}
            />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
```

### 4.5 Update useWebSocket Hook

**File:** `frontend/src/hooks/useWebSocket.ts`

Add thread management functions:

```typescript
// Add these to the existing hook

const switchThread = useCallback((threadId: string) => {
  if (wsRef.current?.readyState === WebSocket.OPEN) {
    wsRef.current.send(JSON.stringify({
      type: 'switch_thread',
      thread_id: threadId
    }));
  }
}, []);

const createNewThread = useCallback((): Promise<string | null> => {
  return new Promise((resolve) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const handler = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'thread_created') {
            wsRef.current?.removeEventListener('message', handler);
            resolve(data.data);
          }
        } catch {}
      };
      wsRef.current.addEventListener('message', handler);
      wsRef.current.send(JSON.stringify({ type: 'new_thread' }));

      // Timeout after 5 seconds
      setTimeout(() => {
        wsRef.current?.removeEventListener('message', handler);
        resolve(null);
      }, 5000);
    } else {
      resolve(null);
    }
  });
}, []);

// Add to return object
return {
  // ... existing
  switchThread,
  createNewThread
};
```

---

## Phase 5: RAG Setup

### 5.1 Run Document Upload

```bash
cd backend

# Create assistant if needed
python scripts/upload_docs.py --create-assistant

# Add the returned assistant ID to .env
# BACKBOARD_ASSISTANT_ID=<your-assistant-id>

# Upload SDK documentation
python scripts/upload_docs.py
```

### 5.2 Verify RAG

Test that RAG is working:

```bash
# Start the backend
uvicorn app.main:app --reload

# In another terminal, test with curl
curl -X POST "http://localhost:8000/threads" | jq
# Note the thread_id

# Then connect via WebSocket and ask:
# "How do I use Backboard memory?"
# "What voices does Speechmatics support?"
```

---

## Phase 6: Polish & Deploy

### 6.1 Add Additional Styles

**Add to:** `frontend/src/styles/main.css`

```css
/* Sidebar styles */
.thread-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: rgba(10, 10, 15, 0.98);
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid rgba(0, 242, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h2 {
  font-family: 'Orbitron', sans-serif;
  font-size: 0.9rem;
  color: var(--cyan);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 2px;
}

.new-thread-btn {
  background: linear-gradient(135deg, var(--cyan), var(--magenta));
  border: none;
  color: white;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-family: 'Space Mono', monospace;
  font-size: 0.8rem;
  transition: all 0.2s;
}

.new-thread-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 0 20px rgba(0, 242, 255, 0.3);
}

.thread-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.thread-item {
  padding: 12px 15px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid transparent;
  transition: all 0.2s;
}

.thread-item:hover {
  background: rgba(0, 242, 255, 0.05);
  border-color: rgba(0, 242, 255, 0.2);
}

.thread-item.active {
  background: rgba(0, 242, 255, 0.1);
  border-color: var(--cyan);
}

.thread-preview {
  font-size: 0.85rem;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 6px;
}

.thread-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
  color: var(--text-muted);
}

/* Mode toggle */
.mode-toggle {
  display: flex;
  gap: 8px;
  margin-bottom: 15px;
  justify-content: center;
}

.mode-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  border: 1px solid rgba(0, 242, 255, 0.3);
  background: transparent;
  color: var(--text-muted);
  border-radius: 8px;
  cursor: pointer;
  font-family: 'Space Mono', monospace;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.mode-btn:hover:not(:disabled) {
  border-color: var(--cyan);
  color: var(--cyan);
}

.mode-btn.active {
  background: rgba(0, 242, 255, 0.1);
  border-color: var(--cyan);
  color: var(--cyan);
}

.mode-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Chat input */
.chat-input-container {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.chat-textarea {
  flex: 1;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(0, 242, 255, 0.2);
  border-radius: 12px;
  padding: 12px 16px;
  color: var(--text);
  font-family: 'Space Mono', monospace;
  font-size: 0.9rem;
  resize: none;
  min-height: 44px;
  max-height: 150px;
  transition: border-color 0.2s;
}

.chat-textarea:focus {
  outline: none;
  border-color: var(--cyan);
}

.chat-textarea::placeholder {
  color: var(--text-muted);
}

.send-button {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, var(--cyan), var(--magenta));
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.send-button:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 0 20px rgba(0, 242, 255, 0.4);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* Layout */
.app-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 280px;
  border-right: 1px solid rgba(0, 242, 255, 0.1);
  flex-shrink: 0;
  transition: transform 0.3s ease;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    height: 100%;
    z-index: 1000;
    transform: translateX(-100%);
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .sidebar-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 999;
  }
}
```

---

## API Specification

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info |
| GET | `/health` | Health check |
| GET | `/threads` | List all threads |
| POST | `/threads` | Create new thread |
| GET | `/threads/{id}` | Get thread with messages |
| DELETE | `/threads/{id}` | Delete thread |

### WebSocket Protocol

**Endpoint:** `ws://host/ws/{user_id}`

**Client → Server:**

| Type | Payload | Mode |
|------|---------|------|
| `text_in` | `{text: string}` | Chat |
| `audio_in` | `{audio: base64}` | Voice |
| `switch_thread` | `{thread_id: string}` | Both |
| `new_thread` | `{}` | Both |

**Server → Client:**

| Type | Payload | Description |
|------|---------|-------------|
| `status` | `string` | connected/transcribing/thinking/synthesizing |
| `transcript` | `string` | Transcribed speech |
| `response` | `string` | Assistant text response |
| `audio_out` | `base64` | Audio response (voice mode) |
| `error` | `string` | Error message |
| `thread_switched` | `string` | Thread ID |
| `thread_created` | `string` | New thread ID |

---

## Testing Checklist

### Backend

- [ ] Health endpoint works
- [ ] WebSocket connects
- [ ] Chat mode: text → response
- [ ] Voice mode: Pipecat pipeline starts
- [ ] Voice mode: audio → transcript → response → audio
- [ ] Thread creation
- [ ] Thread switching
- [ ] Thread listing
- [ ] Memory persistence (ask "what's my name" after telling it)
- [ ] RAG retrieval (ask about Backboard/Speechmatics)

### Frontend

- [ ] App loads
- [ ] WebSocket connects
- [ ] Sidebar shows threads
- [ ] New thread button works
- [ ] Thread selection loads messages
- [ ] Mode toggle switches UI
- [ ] Chat mode: type and send
- [ ] Voice mode: record and send
- [ ] Audio playback works
- [ ] Mobile responsive

### Integration

- [ ] Full chat conversation
- [ ] Full voice conversation
- [ ] Switch threads mid-conversation
- [ ] Memory works across messages
- [ ] RAG returns SDK documentation

---

## Quick Start

```bash
# 1. Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with API keys

# 2. Create assistant and upload docs
python scripts/upload_docs.py --create-assistant
# Copy the assistant ID to .env
python scripts/upload_docs.py

# 3. Start backend
uvicorn app.main:app --reload --port 8000

# 4. Frontend setup (new terminal)
cd frontend
npm install
npm run dev

# 5. Open http://localhost:5173
```

---

## Summary

This implementation uses **Pipecat** as the orchestration layer for voice mode:

1. **Chat Mode**: Direct `BackboardLLMService.get_response()` calls
2. **Voice Mode**: Pipecat pipeline with `SpeechmaticsSTT → BackboardLLM → SpeechmaticsTTS`

The `BackboardLLMService` implements Pipecat's `LLMService` interface, processing `TextFrame` inputs and outputting `TextFrame` responses that flow to TTS.

**Key Benefits:**
- Pipecat handles audio streaming, VAD, interruptions
- Same Backboard service for both modes (shared memory/RAG)
- Clean separation of concerns
- Production-ready pipeline architecture
