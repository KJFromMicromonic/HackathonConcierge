# LiveKit Agents — Custom LLM Plugin API Reference

This document details the exact API for building a custom LLM plugin that integrates
with LiveKit Agents' `AgentSession`. This is what we use to wrap the Backboard API.

---

## Class Hierarchy

```
llm.LLM (ABC)              ← You subclass this (e.g., BackboardLLM)
  └─ .chat() → LLMStream   ← Returns your stream subclass

llm.LLMStream (ABC)         ← You subclass this (e.g., BackboardLLMStream)
  └─ ._run()               ← Push ChatChunk objects to self._event_ch
```

---

## `llm.LLM` Base Class

```python
from livekit.agents import llm

class LLM(ABC, rtc.EventEmitter):
    """Abstract base class for LLM implementations."""

    @property
    def label(self) -> str:
        """Module + class name (auto-generated)."""
        ...

    @property
    def model(self) -> str:
        """Model identifier. Override to return your model name."""
        return "unknown"

    @property
    def provider(self) -> str:
        """Provider identifier. Override to return your provider name."""
        return "unknown"

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
    ) -> "LLMStream":
        """Create a streaming chat completion. Must return an LLMStream."""
        ...

    def prewarm(self) -> None:
        """Optional: Pre-warm connection to the LLM service."""
        pass

    async def aclose(self) -> None:
        """Optional: Async cleanup."""
        pass
```

### What to implement:

1. `__init__()` — Store API keys, config, create HTTP client
2. `model` property — Return model identifier string
3. `provider` property — Return provider identifier string
4. `chat()` — Create and return your `LLMStream` subclass
5. `aclose()` — Clean up HTTP clients

---

## `llm.LLMStream` Base Class

```python
class LLMStream(ABC):
    """Manages streaming response from an LLM call."""

    def __init__(
        self,
        llm: LLM,
        *,
        chat_ctx: ChatContext,
        tools: list[Tool],
        conn_options: APIConnectOptions,
    ) -> None:
        # Internal channel for pushing chunks:
        # self._event_ch  (use self._event_ch.send_nowait(chunk))
        ...

    @abstractmethod
    async def _run(self) -> None:
        """
        Drive the stream. Push ChatChunk objects to self._event_ch.

        The framework handles:
        - Retry logic (via conn_options)
        - Metrics (TTFT, duration)
        - Event emission
        """
        ...

    async def collect(self) -> CollectedResponse:
        """Collect entire stream into a single response."""
        ...

    def to_str_iterable(self) -> AsyncIterable[str]:
        """Convert stream to async iterable of strings."""
        ...

    @property
    def chat_ctx(self) -> ChatContext: ...

    @property
    def tools(self) -> list[Tool]: ...

    # Built-in async iterator protocol
    def __aiter__(self): ...
    async def __anext__(self) -> ChatChunk: ...

    # Built-in async context manager
    async def __aenter__(self): ...
    async def __aexit__(self, *args): ...
```

### What to implement:

1. `__init__()` — Call `super().__init__()`, store any extra params
2. `_run()` — Call your API, parse SSE stream, push `ChatChunk` objects

### Pushing chunks in `_run()`:

```python
async def _run(self) -> None:
    async for token in my_api_stream():
        self._event_ch.send_nowait(
            ChatChunk(
                id="chunk-id",
                delta=ChoiceDelta(
                    role="assistant",
                    content=token,
                ),
            )
        )
```

---

## Data Models

### ChatContext

The conversation history passed to your LLM.

```python
chat_ctx = llm.ChatContext()
chat_ctx.add_message(role="system", content="You are helpful.")
chat_ctx.add_message(role="user", content="Hello!")

# Access messages:
for msg in chat_ctx.messages:
    print(msg.role, msg.content)
```

### ChatChunk

A single streamed chunk from the LLM.

```python
@dataclass
class ChatChunk:
    id: str                              # Chunk identifier
    delta: ChoiceDelta | None = None     # Content delta
    usage: CompletionUsage | None = None # Token usage (optional)
```

### ChoiceDelta

The content of a chunk.

```python
@dataclass
class ChoiceDelta:
    role: ChatRole | None = None                    # "assistant", "user", etc.
    content: str | None = None                      # Text content
    tool_calls: list[FunctionToolCall] = field(default_factory=list)
    extra: dict[str, Any] | None = None
```

### CompletionUsage

Token usage metrics (optional).

```python
@dataclass
class CompletionUsage:
    completion_tokens: int
    prompt_tokens: int
    prompt_cached_tokens: int = 0
    total_tokens: int
```

### CollectedResponse

Full collected response after streaming completes.

```python
@dataclass
class CollectedResponse:
    text: str = ""
    tool_calls: list[FunctionToolCall] = field(default_factory=list)
    usage: CompletionUsage | None = None
```

---

## ChatContext Message Format

When converting `ChatContext` to your API's format:

```python
# Each message has:
msg.role      # "system" | "assistant" | "user" | "tool"
msg.content   # str or None
msg.tool_calls  # list (for assistant messages with function calls)
msg.tool_call_id  # str (for tool response messages)
```

For Backboard API, we only need the last user message since Backboard
manages its own conversation history via thread_id. We extract:

```python
# Get the last user message from ChatContext
user_message = ""
for msg in reversed(chat_ctx.messages):
    if msg.role == "user" and msg.content:
        user_message = msg.content
        break
```

---

## Usage in AgentSession

### As a plugin instance:

```python
session = AgentSession(
    stt="deepgram/nova-3",
    llm=BackboardLLM(
        api_key="...",
        assistant_id="...",
    ),
    tts="cartesia/sonic-3:voice-id",
    vad=silero.VAD.load(),
)
```

### As an llm_node override (alternative):

```python
class MyAgent(Agent):
    async def llm_node(self, chat_ctx, tools, model_settings):
        # Use Backboard directly without the plugin
        async for token in backboard_stream(chat_ctx):
            yield token
```

---

## Error Handling

The framework provides retry logic via `conn_options`:

```python
from livekit.agents.llm import APIConnectOptions

conn_options = APIConnectOptions(
    max_retry=3,
    timeout=30.0,
    retry_interval=0.5,
)
```

In your `_run()` method, raise exceptions for transient errors —
the framework will retry based on `conn_options`.

For fatal errors, raise and the framework will propagate to the session.
