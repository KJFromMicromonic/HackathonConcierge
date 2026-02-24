# Hackathon Concierge - AURA

Voice-powered AI concierge for **Activate Your Voice** hackathon at 42 Ecole Paris.

Built with **Speechmatics** (ASR/TTS) and **Backboard.io** (Memory/RAG).

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐
│   Browser   │────▶│   FastAPI   │────▶│    Speechmatics     │
│  (Vite/TS)  │◀────│  (Python)   │◀────│    (ASR + TTS)      │
└─────────────┘     └──────┬──────┘     └─────────────────────┘
                           │
                           ▼
                   ┌─────────────────────┐
                   │    Backboard.io     │
                   │ (Memory + RAG + LLM)│
                   └─────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Speechmatics API key
- Backboard.io API key

### 1. Clone and setup

```bash
cd HackathonConcierge

# Backend
cd backend
cp .env.example .env
# Edit .env with your API keys
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Run locally

```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Open http://localhost:5173

### 3. Run with Docker

```bash
# Set environment variables
export SPEECHMATICS_API_KEY=your_key
export BACKBOARD_API_KEY=your_key
export BACKBOARD_PROJECT_ID=your_project

# Build and run
docker-compose up --build
```

## Project Structure

```
HackathonConcierge/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Environment config
│   │   ├── websocket_handler.py # WebSocket utilities
│   │   ├── services/
│   │   │   ├── speechmatics.py  # ASR/TTS integration
│   │   │   └── backboard.py     # Memory/RAG integration
│   │   └── models/
│   │       └── schemas.py       # Pydantic models
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main React component
│   │   ├── components/
│   │   │   ├── VoiceInterface.tsx
│   │   │   └── ConversationHistory.tsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts  # WebSocket hook
│   │   ├── services/
│   │   │   └── audioService.ts  # Mic/audio handling
│   │   └── styles/
│   │       └── main.css
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docs/
│   └── rag_content/             # Documents for RAG
│       ├── schedule.md
│       ├── sponsors.md
│       └── faq.md
├── docker-compose.yml
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SPEECHMATICS_API_KEY` | Your Speechmatics API key |
| `BACKBOARD_API_KEY` | Your Backboard.io API key |
| `BACKBOARD_PROJECT_ID` | Your Backboard.io project ID |
| `DEBUG` | Enable debug mode (true/false) |

### Upload RAG Documents

Before the concierge can answer questions, upload the docs in `docs/rag_content/` to your Backboard.io project via their dashboard or API.

## Deployment

### Railway (Recommended)

1. Push to GitHub
2. Create new project on Railway
3. Add backend service from `./backend`
4. Add frontend service from `./frontend`
5. Set environment variables
6. Deploy

### Custom Domain

Point your domain's DNS:
- `www.activateyourvoice.tech` → Frontend
- `api.activateyourvoice.tech` → Backend (WebSocket)

## API Reference

### WebSocket Endpoint

`ws://localhost:8000/ws/{user_id}`

**Messages (Client → Server):**
```json
{"type": "audio_in", "audio": "<base64>"}
{"type": "text_in", "text": "Hello"}
```

**Messages (Server → Client):**
```json
{"type": "status", "data": "transcribing|thinking|synthesizing|ready"}
{"type": "transcript", "data": "User's spoken text"}
{"type": "response", "data": "AURA's response"}
{"type": "audio_out", "audio": "<base64>"}
{"type": "error", "data": "Error message"}
```

## License

MIT - Built for Activate Your Voice hackathon.
