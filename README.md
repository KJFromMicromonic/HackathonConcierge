# AURA — AI Voice Concierge

AURA (AI-powered Universal Resource Assistant) is a dual-mode AI concierge for hackathons and events. It provides both text chat and real-time voice conversation, powered by persistent memory and document retrieval.

Built with **Speechmatics** (STT), **ElevenLabs** (TTS), **Backboard.io** (Memory + RAG), and **LiveKit** (Voice).

## How It Works

AURA has two modes:

- **Chat Mode** — Text conversation with streaming responses, model selection, and document-backed answers
- **Voice Mode** — Real-time voice conversation via WebRTC with sub-second latency

Each user gets a personal AI assistant with isolated memory — AURA remembers your project, your team, and your preferences across sessions.

## Architecture

```
┌─────────────────┐     ┌────────────────┐     ┌──────────────────┐
│    Frontend      │────▶│   Backend API  │────▶│  Backboard.io    │
│  React + Vite    │◀────│   FastAPI      │◀────│  Memory + RAG    │
└────────┬────────┘     └────────────────┘     └────────┬─────────┘
         │                                              │
         │ WebRTC                                       ▼
         │                                     ┌────────────────┐
    ┌────▼────────────┐                        │ LLM Providers  │
    │  LiveKit Cloud   │───────────────────────▶│ Claude / Grok  │
    │  Voice Agent     │                        │ GPT / Gemini   │
    │  STT + TTS       │                        └────────────────┘
    └─────────────────┘
```

### Key Components

| Component | Role | Technology |
|-----------|------|-----------|
| **Frontend** | Chat UI, voice interface, model selector | React, TypeScript, Vite |
| **Backend API** | WebSocket chat, REST endpoints, notifications | FastAPI, Python |
| **Voice Agent** | Real-time voice pipeline | LiveKit Agents, Speechmatics STT, ElevenLabs TTS |
| **Memory + RAG** | Persistent memory, document retrieval, LLM routing | Backboard.io |
| **Auth + Database** | User auth, session storage, team data | Supabase |

## Features

- **Per-user AI assistants** with isolated memory and shared knowledge base
- **Multi-model support** — Switch between Claude, GPT-4o, Grok, Gemini per message
- **Real-time voice** — Speechmatics STT + ElevenLabs TTS + Silero VAD
- **Proactive notifications** — Activity feed events pushed to chat in real-time
- **Document-backed answers** — Keyword-based context injection from shared docs
- **Streaming responses** with typing indicator and auto-scroll
- **First-login provisioning** with real-time progress UI
- **Seamless auth** — Token passthrough from external apps (no re-login)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- API keys: Speechmatics, Backboard.io, ElevenLabs, Supabase, LiveKit

### Setup

```bash
git clone <repo-url>
cd HackathonConcierge

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys

# Frontend
cd ../frontend
npm install
cp .env.example .env
# Edit .env with Supabase URL and anon key
```

### Run Locally

```bash
# Terminal 1 — Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev

# Terminal 3 — Voice Agent (optional, for voice mode)
cd backend
python livekitapp/agent.py dev
```

### Verify Shared Docs

```bash
cd backend
python scripts/prime_shared_docs.py
```

This checks that all knowledge base documents are present and ready for upload to new user assistants.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `BACKBOARD_API_KEY` | Backboard.io API key |
| `BACKBOARD_BASE_URL` | Backboard API URL |
| `CHAT_LLM_PROVIDER` | Chat LLM provider (e.g. `anthropic`, `openai`) |
| `CHAT_MODEL_NAME` | Chat model name |
| `VOICE_LLM_PROVIDER` | Voice LLM provider (e.g. `xai`) |
| `VOICE_MODEL_NAME` | Voice model name |
| `SPEECHMATICS_API_KEY` | Speechmatics API key |
| `ELEVEN_API_KEY` | ElevenLabs API key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `LIVEKIT_URL` | LiveKit Cloud WebSocket URL |
| `LIVEKIT_API_KEY` | LiveKit API key |
| `LIVEKIT_API_SECRET` | LiveKit API secret |

### Frontend (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key |

## Project Structure

```
HackathonConcierge/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app + WebSocket endpoint
│   │   ├── config.py                # Settings from .env
│   │   ├── auth.py                  # JWT auth
│   │   ├── assistant_template.py    # System prompt + doc config
│   │   ├── websocket_handler.py     # Connection manager
│   │   ├── models/
│   │   │   └── chat_models.py       # LLM model catalog
│   │   └── services/
│   │       ├── backboard_llm.py     # Streaming LLM service
│   │       ├── user_assistant_service.py  # Per-user provisioning
│   │       ├── activity_poller.py   # Real-time notifications
│   │       └── context_injector.py  # Doc-based context injection
│   ├── livekitapp/
│   │   ├── agent.py                 # Voice agent entry point
│   │   ├── backboard_llm.py         # LLM plugin for LiveKit
│   │   └── session_store.py         # Voice session management
│   ├── shared_docs/                 # Knowledge base documents
│   ├── Dockerfile                   # Voice agent container
│   ├── Dockerfile.api               # API server container
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/              # UI components
│   │   ├── hooks/                   # WebSocket + LiveKit hooks
│   │   ├── contexts/                # Auth context
│   │   └── lib/                     # Supabase client
│   └── package.json
└── README.md
```

## Deployment

### Frontend
Deploy to Vercel with root directory set to `frontend`. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` as environment variables.

### Backend API
Deploy via Docker on any VPS:
```bash
docker build -f Dockerfile.api -t aura-backend .
docker run -d --name aura-backend --env-file .env -p 8000:8000 --restart unless-stopped aura-backend
```

### Voice Agent
Deploy to LiveKit Cloud:
```bash
lk agent deploy
```

## WebSocket Protocol

**Client → Server:**
```json
{"type": "text_in", "text": "...", "model_id": "claude-sonnet"}
{"type": "switch_thread", "thread_id": "..."}
{"type": "new_thread"}
```

**Server → Client:**
```json
{"type": "status", "data": "connected|thinking"}
{"type": "response_delta", "data": "token"}
{"type": "response_end", "data": "full response"}
{"type": "notification", "data": {"notification_type": "...", "message": "..."}}
{"type": "provisioning", "data": {"step": "...", "message": "...", "progress": 0, "total": 15}}
```

## Adding Knowledge Base Documents

1. Place markdown files in `backend/shared_docs/`
2. Add filenames to `SHARED_DOCUMENTS` in `backend/app/assistant_template.py`
3. Add keyword mappings in `backend/app/services/context_injector.py`
4. Run `python scripts/prime_shared_docs.py` to verify
5. New users will automatically get the updated docs on first login

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, TypeScript, remark-gfm |
| Backend | FastAPI, Python 3.11, httpx, loguru |
| Voice | LiveKit Agents 1.4, Speechmatics STT, ElevenLabs TTS, Silero VAD |
| LLM | Backboard.io (supports Claude, GPT, Grok, Gemini + 1800 more) |
| Auth | Supabase Auth |
| Database | Supabase PostgreSQL |

## License

MIT
