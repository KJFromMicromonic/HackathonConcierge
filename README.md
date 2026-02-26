# AURA — AI Voice Concierge

AURA (AI-powered Universal Resource Assistant) is a dual-mode AI concierge that combines text chat and real-time voice conversation, powered by persistent memory and document retrieval.

Built with **Speechmatics** (STT), **ElevenLabs** (TTS), **Backboard.io** (Memory + RAG), and **LiveKit** (Voice).

---

## Table of Contents

- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Tutorial: Building with Backboard.io](#tutorial-building-with-backboardio)
- [Tutorial: Building with Speechmatics](#tutorial-building-with-speechmatics)
- [Combining Backboard + Speechmatics](#combining-backboard--speechmatics)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Deployment](#deployment)
- [WebSocket Protocol](#websocket-protocol)

---

## How It Works

AURA has two modes:

- **Chat Mode** — Text conversation with streaming responses, model selection, and document-backed answers
- **Voice Mode** — Real-time voice via WebRTC with sub-second latency

Each user gets a personal AI assistant with isolated memory — AURA remembers your project, team, and preferences across sessions.

```
┌─────────────────┐     ┌────────────────┐     ┌──────────────────┐
│    Frontend      │────▶│   Backend API  │────▶│  Backboard.io    │
│  React + Vite    │◀────│   FastAPI      │◀────│  Memory + RAG    │
└────────┬────────┘     └────────────────┘     └────────┬─────────┘
         │                                              │
         │ WebRTC                                       ▼
    ┌────▼────────────┐                        ┌────────────────┐
    │  LiveKit Cloud   │───────────────────────▶│ LLM Providers  │
    │  Voice Agent     │                        │ Claude / Grok  │
    └─────────────────┘                        └────────────────┘
```

---

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
cp .env.example .env      # Edit with your API keys

# Frontend
cd ../frontend
npm install
cp .env.example .env      # Edit with Supabase credentials
```

### Run

```bash
# Terminal 1 — Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev

# Terminal 3 — Voice Agent (optional)
cd backend && python livekitapp/agent.py dev
```

Open http://localhost:5173

---

## Tutorial: Building with Backboard.io

Backboard gives your AI **persistent memory** and **document retrieval (RAG)** that works across conversations. Think of it as the brain behind your assistant.

### 1. Install and Connect

```bash
pip install backboard-sdk
```

```python
from backboard import BackboardClient

client = BackboardClient(api_key="YOUR_BACKBOARD_API_KEY")
```

**REST API alternative** — all endpoints use `https://app.backboard.io/api` with header `X-API-Key: your_key`.

### 2. Create an Assistant

An assistant defines your AI's behavior — system prompt, personality, and what documents it can access.

```python
assistant = await client.create_assistant(
    name="My Hackathon Bot",
    description="Helps with hackathon questions",
    system_prompt="You are a helpful assistant for hackathon participants.",
    embedding_provider="openai",
    embedding_model_name="text-embedding-3-small",
    embedding_dims=1536,
)
assistant_id = str(assistant.assistant_id)
```

### 3. Start a Conversation (Threads)

Each conversation lives in a thread. Threads belong to an assistant and maintain full message history.

```python
# Create a thread
thread = await client.create_thread(assistant_id)
thread_id = str(thread.thread_id)

# Send a message and get a response
response = await client.add_message(
    thread_id=thread_id,
    content="What are the hackathon rules?",
    llm_provider="anthropic",          # or "openai", "xai", "google"
    model_name="claude-sonnet-4-5-20250929",
    memory="auto"                      # enables persistent memory
)

print(response.content)
```

**Key concept:** You can switch LLM providers per message. The thread context, memory, and documents stay the same — only the "brain" changes.

### 4. Persistent Memory

Memory survives across conversations. Ask the bot about something today, and it remembers tomorrow.

```python
# Memory is automatic with memory="auto"
await client.add_message(
    thread_id=thread_id,
    content="My team is building a voice accessibility tool with Python",
    memory="auto"   # Backboard extracts and stores key facts
)

# Later, in a different conversation:
response = await client.add_message(
    thread_id=new_thread_id,
    content="What am I working on?",
    memory="auto"   # Retrieves: "User's team is building a voice accessibility tool"
)
```

**Memory modes:**

| Mode | What it does |
|------|-------------|
| `"auto"` | Read existing memories AND save new ones |
| `"readonly"` | Read memories but don't save (faster) |
| `None` | No memory at all (fastest) |

**Manual memory management:**

```python
# Add a memory explicitly
await client.add_memory(
    assistant_id=assistant_id,
    content="User prefers Python over JavaScript"
)

# List all memories
memories = await client.list_memories(assistant_id=assistant_id)

# Delete a memory
await client.delete_memory(memory_id="mem_abc123")
```

### 5. Document RAG

Upload documents and the assistant can answer questions about them.

```python
# Upload a document
doc = await client.upload_document_to_assistant(
    assistant_id=assistant_id,
    file_path="hackathon_rules.pdf"
)

# Documents are automatically chunked, embedded, and indexed
# Now the assistant can answer questions about the content:
response = await client.add_message(
    thread_id=thread_id,
    content="What are the judging criteria?",
    memory="auto"
)
# Response will cite the uploaded document
```

**Supported formats:** PDF, DOCX, TXT, MD, JSON, CSV, Python, and more.

### 6. Streaming Responses

For real-time UX, stream tokens as they arrive:

```python
async for token in client.stream_message(
    thread_id=thread_id,
    content="Explain how to use the Speechmatics API",
    llm_provider="openai",
    model_name="gpt-4o",
    memory="auto"
):
    print(token, end="", flush=True)
```

### 7. REST API Quick Reference

All endpoints require `X-API-Key` header.

| Action | Method | Endpoint |
|--------|--------|----------|
| Create assistant | POST | `/assistants` |
| List assistants | GET | `/assistants` |
| Create thread | POST | `/assistants/{id}/threads` |
| Send message | POST | `/threads/{id}/messages` |
| List memories | GET | `/assistants/{id}/memories` |
| Add memory | POST | `/assistants/{id}/memories` |
| Upload document | POST | `/assistants/{id}/documents` |
| Get document status | GET | `/documents/{id}` |

---

## Tutorial: Building with Speechmatics

Speechmatics provides **speech-to-text**, **text-to-speech**, and **voice agent** capabilities in 55+ languages with ultra-low latency.

### 1. Install

```bash
# Pick what you need:
pip install speechmatics-rt      # Real-time STT
pip install speechmatics-batch   # File transcription
pip install speechmatics-tts     # Text-to-Speech
pip install speechmatics-voice   # Voice Agents
```

Get your API key from [portal.speechmatics.com](https://portal.speechmatics.com).

### 2. Real-Time Speech-to-Text

Transcribe live audio with ~150ms latency.

```python
import asyncio
from speechmatics.rt import RealtimeClient, TranscriptionConfig

async def transcribe():
    client = RealtimeClient(api_key="YOUR_SPEECHMATICS_API_KEY")

    config = TranscriptionConfig(
        language="en",
        enable_partials=True,   # Get interim results as user speaks
        max_delay=2.0
    )

    @client.on("partial_transcript")
    def on_partial(msg):
        print(f"[typing...] {msg['metadata']['transcript']}")

    @client.on("final_transcript")
    def on_final(msg):
        print(f"[final] {msg['metadata']['transcript']}")

    with open("audio.wav", "rb") as f:
        await client.transcribe(f, config)

asyncio.run(transcribe())
```

### Real-Time Message Flow

```
┌──────────────┐                              ┌──────────────────┐
│    CLIENT    │                              │   SPEECHMATICS   │
└──────┬───────┘                              └────────┬─────────┘
       │  ─────── WebSocket Connect ─────▶            │
       │  ─────── StartRecognition ──────▶            │
       │           (config, audio format)              │
       │  ◀─────── RecognitionStarted ────            │
       │                                               │
       │  ═══════ Audio Chunks (binary) ══▶           │
       │  ◀─────── AudioAdded (ack) ──────            │
       │  ◀─────── AddPartialTranscript ──            │
       │           (interim results)                   │
       │  ◀─────── AddTranscript ─────────            │
       │           (final results)                     │
       │                                               │
       │  ─────── EndOfStream ────────────▶           │
       │  ◀─────── EndOfTranscript ───────            │
```

### 3. Text-to-Speech

Convert text to natural speech.

```python
import asyncio
from speechmatics.tts import AsyncClient, Voice, OutputFormat

async def speak():
    client = AsyncClient(api_key="YOUR_SPEECHMATICS_API_KEY")

    response = await client.generate(
        text="Welcome to the hackathon! Let's build something amazing.",
        voice=Voice.SARAH,
        output_format=OutputFormat.WAV_16000
    )

    with open("output.wav", "wb") as f:
        f.write(await response.read())

    await client.close()

asyncio.run(speak())
```

**Available voices:** Sarah (EN-US Female), James (EN-US Male), Emma (EN-UK Female), Oliver (EN-UK Male)

### 4. Streaming TTS

For real-time voice responses:

```python
async for audio_chunk in client.stream(
    text="This streams audio as it's generated.",
    voice=Voice.SARAH
):
    # Send each chunk to the speaker immediately
    play_audio(audio_chunk)
```

### 5. Voice Agents

Build a conversational AI with smart turn detection:

```python
from speechmatics.voice import VoiceAgent, AgentConfig

config = AgentConfig(
    language="en",
    voice="sarah",
    turn_detection="smart",   # ML-based: knows when user is done speaking
    diarization=True           # Identify different speakers
)

agent = VoiceAgent(api_key="YOUR_API_KEY", config=config)

@agent.on("turn_end")
async def on_turn_end(transcript):
    # User finished speaking — process with your LLM
    response = await get_llm_response(transcript)
    await agent.speak(response)

await agent.start()
```

### 6. Configuration Options

```python
config = TranscriptionConfig(
    language="en",                # 55+ language codes
    enable_partials=True,         # Interim results
    max_delay=5.0,                # Seconds before forcing result
    enable_entities=True,         # Extract dates, currencies, etc.
    diarization="speaker",        # Who said what
    operating_point="enhanced",   # "standard" (fast) or "enhanced" (accurate)
    additional_vocab=[            # Custom words
        {"content": "Backboard", "sounds_like": ["back board"]},
        {"content": "Speechmatics"}
    ]
)
```

---

## Combining Backboard + Speechmatics

The real power is combining both — voice input via Speechmatics, intelligent responses via Backboard with memory and RAG.

### Pattern: Voice-Powered AI with Memory

```python
import asyncio
from speechmatics.rt import RealtimeClient, TranscriptionConfig
from backboard import BackboardClient

async def voice_ai():
    # Initialize both
    stt = RealtimeClient(api_key="SPEECHMATICS_KEY")
    llm = BackboardClient(api_key="BACKBOARD_KEY")

    # Create assistant with personality + documents
    assistant = await llm.create_assistant(
        name="Voice Assistant",
        system_prompt="You are a helpful voice assistant. Keep responses brief."
    )

    # Upload knowledge base
    await llm.upload_document_to_assistant(
        str(assistant.assistant_id), "knowledge_base.pdf"
    )

    # Start conversation thread
    thread = await llm.create_thread(str(assistant.assistant_id))

    # When user finishes speaking:
    async def handle_speech(transcript):
        # Send to Backboard — gets memory + RAG + LLM response
        response = await llm.add_message(
            thread_id=str(thread.thread_id),
            content=transcript,
            llm_provider="xai",
            model_name="grok-4-1-fast-non-reasoning",  # Fast for voice
            memory="auto"
        )
        print(f"AI: {response.content}")
        # → Send response.content to TTS

    # Transcribe audio
    config = TranscriptionConfig(language="en", enable_partials=True)

    @stt.on("final_transcript")
    def on_final(msg):
        text = msg["metadata"]["transcript"]
        asyncio.create_task(handle_speech(text))

    with open("audio.wav", "rb") as f:
        await stt.transcribe(f, config)

asyncio.run(voice_ai())
```

### How AURA Uses This Pattern

AURA's voice mode runs this exact architecture via LiveKit:

```
Microphone → Speechmatics STT → Backboard (Grok 4 Fast + Memory) → ElevenLabs TTS → Speaker
```

- **STT:** Speechmatics real-time with partial transcripts
- **LLM:** Grok 4 Fast via Backboard (fast for voice)
- **Memory:** Backboard auto-mode (remembers user context)
- **TTS:** ElevenLabs Flash v2.5 for lowest latency
- **VAD:** Silero for voice activity detection

Chat mode uses the same Backboard assistant (same memory, same docs) but with Claude Sonnet 4.5 for deeper reasoning.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `BACKBOARD_API_KEY` | Backboard.io API key |
| `BACKBOARD_BASE_URL` | Backboard API URL |
| `CHAT_LLM_PROVIDER` | Chat LLM provider (e.g. `anthropic`) |
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

---

## Project Structure

```
HackathonConcierge/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app + WebSocket
│   │   ├── config.py                # Settings from .env
│   │   ├── assistant_template.py    # System prompt + doc config
│   │   └── services/
│   │       ├── backboard_llm.py     # Streaming LLM service
│   │       ├── user_assistant_service.py  # Per-user provisioning
│   │       ├── activity_poller.py   # Real-time notifications
│   │       └── context_injector.py  # Doc context injection
│   ├── livekitapp/
│   │   ├── agent.py                 # Voice agent (Speechmatics + Backboard)
│   │   └── backboard_llm.py         # LLM plugin for LiveKit
│   ├── shared_docs/                 # Knowledge base documents
│   ├── Dockerfile.api               # API server container
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/              # Chat, Voice, Model selector
│   │   ├── hooks/                   # WebSocket + LiveKit hooks
│   │   └── contexts/                # Auth
│   └── package.json
└── README.md
```

---

## Deployment

**Frontend** — Deploy to Vercel with root directory `frontend`. Set env vars in Vercel dashboard.

**Backend API** — Docker on any VPS:
```bash
docker build -f Dockerfile.api -t aura-backend .
docker run -d --name aura-backend --env-file .env -p 8000:8000 --restart unless-stopped aura-backend
```

**Voice Agent** — LiveKit Cloud:
```bash
lk agent deploy
```

---

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

---

## Adding Knowledge Base Documents

1. Place markdown files in `backend/shared_docs/`
2. Add filenames to `SHARED_DOCUMENTS` in `backend/app/assistant_template.py`
3. Add keyword mappings in `backend/app/services/context_injector.py`
4. Run `python scripts/prime_shared_docs.py` to verify

---

## License

MIT
