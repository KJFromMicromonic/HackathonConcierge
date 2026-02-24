# LiveKit Agents Framework - Complete Guide

## Overview

LiveKit Agents is a Python framework for building real-time, multimodal voice AI agents.
Agents join LiveKit "rooms" as WebRTC participants, processing audio through an
STT → LLM → TTS pipeline and streaming synthesized audio back to users.

**Key difference from Pipecat**: LiveKit handles WebRTC transport natively via its
SFU (Selective Forwarding Unit), so you don't need custom WebSocket serializers or
browser audio encoding — the LiveKit client SDKs handle all of that.

---

## Architecture

```
┌─────────────┐    WebRTC     ┌──────────────┐    HTTP/WS    ┌─────────────┐
│  Browser /   │ ◄──────────► │  LiveKit SFU  │ ◄──────────► │   Agent     │
│  Mobile App  │              │  (Cloud/OSS)  │              │  (Python)   │
└─────────────┘              └──────────────┘              └─────────────┘
                                                                  │
                                                    ┌─────────────┼──────────────┐
                                                    ▼             ▼              ▼
                                                  STT           LLM            TTS
                                               (Deepgram)   (Backboard)    (Cartesia)
```

### Core Components

| Component | Description |
|---|---|
| **AgentServer** | Main process that coordinates job scheduling and dispatch |
| **JobContext** | Per-room context providing access to the room and lifecycle |
| **AgentSession** | Orchestrator for the STT-LLM-TTS pipeline |
| **Agent** | Your LLM-based app with instructions, tools, and pipeline node overrides |
| **RoomIO** | Bridges AgentSession ↔ LiveKit room (audio tracks) |

### Agent Lifecycle

1. Agent server registers with LiveKit Cloud
2. Room created → dispatch request sent to agent server
3. Agent server spawns job subprocess that joins the room via WebRTC
4. AgentSession created and started (establishes STT-LLM-TTS pipeline)
5. Agent cycles through: `listening` → `thinking` → `speaking`
6. Graceful shutdown on disconnect

---

## Free Tier ("Build Plan")

**Cost: $0/month, no credit card required**

| Resource | Included |
|---|---|
| Agent session minutes | 1,000/month |
| Concurrent agent sessions | 5 |
| Agent deployments | 1 |
| WebRTC participant minutes | 5,000/month |
| Concurrent connections | 100 |
| Inference credits | $2.50 (~50 min) |
| Recording minutes | 1,000/month |
| US local phone numbers | 1 free |
| Data transfer | 50 GB |

**Limitations**: No team collaboration, no instant rollback, no cold start prevention,
community support only.

---

## Installation

```bash
# Core + plugins
pip install \
  "livekit-agents[silero,turn-detector]~=1.3" \
  "livekit-plugins-noise-cancellation~=0.2" \
  "python-dotenv"

# CLI for cloud management
# Windows:
winget install LiveKit.LiveKitCLI
# macOS:
brew install livekit-cli
# Linux:
curl -sSL https://get.livekit.io/cli | bash

# Authenticate with LiveKit Cloud
lk cloud auth

# Generate .env.local with credentials
lk app env -w
```

### Environment Variables

```env
LIVEKIT_API_KEY=<your key>
LIVEKIT_API_SECRET=<your secret>
LIVEKIT_URL=wss://<your-project>.livekit.cloud

# For Backboard (our custom LLM)
BACKBOARD_API_KEY=<your key>
BACKBOARD_BASE_URL=https://app.backboard.io/api

# For STT/TTS (if using specific providers)
DEEPGRAM_API_KEY=<key>      # optional, can use LiveKit inference
CARTESIA_API_KEY=<key>      # optional, can use LiveKit inference
```

---

## Minimal Agent Example

```python
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent, room_io
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv(".env.local")

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="You are a helpful voice AI assistant.",
        )

    async def on_enter(self):
        # Greet the user when they join
        self.session.generate_reply(allow_interruptions=False)

server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        stt="deepgram/nova-3:multi",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-3:voice-id",
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )
    await session.start(
        room=ctx.room,
        agent=MyAgent(),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )

if __name__ == "__main__":
    agents.cli.run_app(server)
```

### Running

```bash
# Download model files (Silero VAD, Turn Detector)
python agent.py download-files

# Local testing (console mode, no LiveKit server needed)
python agent.py console

# Development (connects to LiveKit Cloud)
python agent.py dev

# Production
python agent.py start
```

---

## Pipeline Nodes (Customization Points)

The three customizable nodes in the pipeline:

### 1. STT Node — Speech-to-Text

```python
async def stt_node(
    self,
    audio: AsyncIterable[rtc.AudioFrame],
    model_settings: ModelSettings
) -> Optional[AsyncIterable[stt.SpeechEvent]]:
```

### 2. LLM Node — Language Model (most relevant for Backboard)

```python
async def llm_node(
    self,
    chat_ctx: llm.ChatContext,
    tools: list[FunctionTool],
    model_settings: ModelSettings
) -> AsyncIterable[llm.ChatChunk | str]:
```

You can yield plain `str` for simple text, or `llm.ChatChunk` for richer output.

### 3. TTS Node — Text-to-Speech

```python
async def tts_node(
    self,
    text: AsyncIterable[str],
    model_settings: ModelSettings
) -> AsyncIterable[rtc.AudioFrame]:
```

### Lifecycle Hooks

- `on_enter()` — Agent becomes active (use for greetings)
- `on_exit()` — Agent transitioning out (cleanup)
- `on_user_turn_completed()` — User finished speaking (RAG injection point)

---

## Custom LLM Plugin API

Two approaches for integrating a custom LLM:

### Approach A: Override `llm_node` on Agent (Simpler)

Best when you just want to swap the LLM without building a reusable plugin.

```python
class MyAgent(Agent):
    async def llm_node(self, chat_ctx, tools, model_settings):
        async for token in my_custom_api(chat_ctx.messages):
            yield token  # yield str directly
```

### Approach B: Subclass `llm.LLM` + `llm.LLMStream` (Reusable Plugin)

Best for a reusable component that can be passed to `AgentSession(llm=...)`.

**Base classes to implement:**

```python
class llm.LLM(ABC):
    @property
    def model(self) -> str: ...
    @property
    def provider(self) -> str: ...

    @abstractmethod
    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list[Tool] | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls: NotGivenOr[bool] = NOT_GIVEN,
        tool_choice: NotGivenOr[ToolChoice] = NOT_GIVEN,
        extra_kwargs: NotGivenOr[dict[str, Any]] = NOT_GIVEN,
    ) -> LLMStream: ...

    async def aclose(self) -> None: ...
```

```python
class llm.LLMStream(ABC):
    def __init__(self, llm, *, chat_ctx, tools, conn_options): ...

    @abstractmethod
    async def _run(self) -> None:
        # Push ChatChunk objects to self._event_ch
        ...

    # Async iterator + context manager protocols built in
```

**Key data models:**

```python
@dataclass
class ChatChunk:
    id: str
    delta: ChoiceDelta | None = None
    usage: CompletionUsage | None = None

@dataclass
class ChoiceDelta:
    role: ChatRole | None = None
    content: str | None = None
    tool_calls: list[FunctionToolCall] = field(default_factory=list)
```

See `livekitapp/backboard_llm.py` for our full implementation.

---

## Key Differences: Pipecat vs LiveKit Agents

| Aspect | Pipecat (current) | LiveKit Agents (new) |
|---|---|---|
| **Transport** | Custom WebSocket + serializer | WebRTC via LiveKit rooms |
| **Pipeline** | Frame-based with processors | Node-based (stt/llm/tts nodes) |
| **Custom LLM** | Extend `LLMService`, override `process_frame()` | Subclass `llm.LLM`/`LLMStream` |
| **Frame types** | TranscriptionFrame, LLMTextFrame | SpeechEvent, ChatChunk |
| **Audio encoding** | Manual base64 PCM over WS | Handled by LiveKit SDK |
| **VAD** | Silero or STT-integrated | Silero + multilingual turn detector |
| **Deployment** | Manual Docker | `lk agent create` for cloud |
| **Free tier** | N/A (self-hosted) | 1,000 agent min/month |

---

## References

- [LiveKit Agents Docs](https://docs.livekit.io/agents/)
- [Voice AI Quickstart](https://docs.livekit.io/agents/start/voice-ai-quickstart/)
- [Custom LLM / Pipeline Nodes](https://docs.livekit.io/agents/build/nodes/)
- [Agent Sessions](https://docs.livekit.io/agents/logic/sessions/)
- [LLM API Reference](https://docs.livekit.io/reference/python/livekit/agents/llm/index.html)
- [GitHub: livekit/agents](https://github.com/livekit/agents)
- [GitHub: agent-starter-python](https://github.com/livekit-examples/agent-starter-python)
- [LiveKit Pricing](https://livekit.io/pricing)
