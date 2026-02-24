# CLAUDE.md - Hackathon Concierge

This file provides context for Claude Code instances working in this repository.

## Project Overview

**Hackathon Concierge** is a voice-powered AI assistant for the "Activate Your Voice" hackathon. It uses:
- **Backboard.io** - LLM service with persistent memory, threads, and RAG
- **Speechmatics** - Speech-to-text (ASR) and text-to-speech (TTS)
- **Pipecat** - Pipeline orchestration for voice AI

The app has two modes:
1. **Chat Mode** - Text-based conversation (like ChatGPT/Claude)
2. **Voice Mode** - Real-time voice conversation via Pipecat pipeline

## Repository Structure

```
HackathonConcierge/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI app, WebSocket endpoint
│   │   ├── config.py          # Settings (pydantic-settings)
│   │   ├── models/
│   │   │   └── schemas.py     # Pydantic models
│   │   └── services/
│   │       ├── backboard_llm.py   # LLM service (Backboard API)
│   │       └── session_store.py   # Thread/session management
│   ├── scripts/
│   │   └── upload_docs.py     # Upload docs to Backboard RAG
│   ├── requirements.txt
│   └── .env                   # Environment variables (not in git)
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── main.tsx
│   │   ├── components/
│   │   │   └── VoiceInterface.tsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts
│   │   └── services/
│   │       └── audioService.ts
│   └── package.json
├── docs/                       # Documentation
│   ├── BACKBOARD_SDK_DOCUMENTATION.md
│   ├── SPEECHMATICS_DOCUMENTATION.md
│   └── rag_content/           # Content for RAG
│       ├── schedule.md
│       ├── sponsors.md
│       └── faq.md
└── IMPLEMENTATION_PLAN.md      # Detailed implementation plan
```

## Build and Run Commands

### Backend

```bash
cd backend

# Create virtual environment (first time)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# Upload documents to Backboard RAG
python scripts/upload_docs.py

# Create new assistant (if needed)
python scripts/upload_docs.py --create-assistant
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## Environment Variables

Create `backend/.env` with:

```env
# Speechmatics API
SPEECHMATICS_API_KEY=your_key_here

# Backboard.io API
BACKBOARD_BASE_URL=https://app.backboard.io/api
BACKBOARD_API_KEY=your_key_here
BACKBOARD_ASSISTANT_ID=your_assistant_id  # Leave empty to create on startup
BACKBOARD_LLM_PROVIDER=xai                # or openai, anthropic, google
BACKBOARD_MODEL_NAME=grok-4-1-fast-non-reasoning

# App settings
DEBUG=true
```

## Architecture

### Voice Pipeline (Pipecat)
```
Microphone → VAD → Speechmatics STT → BackboardLLMService → Speechmatics TTS → Speaker
```

### Chat Mode (Direct)
```
Text Input → BackboardLLMService.get_response() → Text Output
```

### Key Services

1. **BackboardLLMService** (`app/services/backboard_llm.py`)
   - Handles LLM requests via Backboard API
   - Manages user context and thread IDs
   - Methods: `get_response()`, `get_response_stream()`

2. **SessionStore** (`app/services/session_store.py`)
   - Maps user_id → thread_id
   - Creates Backboard threads on demand
   - In-memory storage (use Redis in production)

### WebSocket Protocol

Client → Server:
- `{type: "text_in", text: "..."}`
- `{type: "audio_in", audio: "base64..."}`

Server → Client:
- `{type: "status", data: "connected"|"thinking"|"transcribing"|"synthesizing"}`
- `{type: "transcript", data: "user said..."}`
- `{type: "response", data: "assistant response..."}`
- `{type: "audio_out", audio: "base64..."}`
- `{type: "error", data: "error message"}`

## Implementation Status

Current state:
- Backend: Basic WebSocket endpoint works, text mode functional
- Frontend: Basic React app with voice interface component
- Voice mode: TODO - integrate Pipecat pipeline

See `IMPLEMENTATION_PLAN.md` for detailed implementation phases.

## Key Dependencies

### Backend
- `fastapi` - Web framework
- `backboard-sdk` - Backboard.io client
- `speechmatics-python` - Speechmatics client
- `pipecat-ai[speechmatics,websocket,silero]` - Voice pipeline orchestration
- `httpx` - Async HTTP client

### Frontend
- `react` - UI framework
- `vite` - Build tool

## Backboard SDK Quick Reference

```python
from backboard import BackboardClient

client = BackboardClient(api_key="...")

# Create thread
thread = await client.create_thread(assistant_id="...")

# Send message with streaming
async for token in client.stream_message(
    thread_id=thread.thread_id,
    content="Hello",
    llm_provider="openai",
    model_name="gpt-4o"
):
    print(token, end="")

# Enable memory
response = await client.send_message(..., memory="auto")
```

## Speechmatics Quick Reference

```python
from speechmatics.client import WebsocketClient
from speechmatics.models import (
    ConnectionSettings,
    TranscriptionConfig,
    AudioSettings
)

# Real-time STT
client = WebsocketClient(ConnectionSettings(api_key="..."))
await client.connect(TranscriptionConfig(language="en"))

# Send audio
await client.send_audio(audio_bytes)
```

## Common Tasks

### Adding a new API endpoint
1. Add route in `backend/app/main.py`
2. Add Pydantic schema in `backend/app/models/schemas.py` if needed

### Adding RAG content
1. Add markdown file to `docs/rag_content/`
2. Add path to `doc_files` list in `scripts/upload_docs.py`
3. Run `python scripts/upload_docs.py`

### Changing LLM model
Update `BACKBOARD_LLM_PROVIDER` and `BACKBOARD_MODEL_NAME` in `.env`

## Notes for Claude Code

- The Backboard SDK is installed in the virtual environment, not in the codebase
- Pipecat integration is partially complete - see `IMPLEMENTATION_PLAN.md` Phase 1-2
- Frontend needs thread sidebar and mode toggle components
- Audio processing currently has TODO placeholder in `main.py:128`
