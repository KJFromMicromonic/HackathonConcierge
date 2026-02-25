# Speechmatics — Real-Time Speech-to-Text

Real-time streaming ASR (Automatic Speech Recognition) for live audio with ultra-low latency (~150ms).

**Package:** `pip install speechmatics-rt`

---

## Basic Example

```python
import asyncio
from speechmatics.rt import RealtimeClient, TranscriptionConfig

async def transcribe_realtime():
    client = RealtimeClient(api_key="YOUR_API_KEY")

    config = TranscriptionConfig(
        language="en",
        enable_partials=True,  # Get interim results
        max_delay=2.0          # Max seconds before forcing result
    )

    # Event handlers
    @client.on("partial_transcript")
    def on_partial(msg):
        print(f"[Partial] {msg['metadata']['transcript']}")

    @client.on("final_transcript")
    def on_final(msg):
        print(f"[Final] {msg['metadata']['transcript']}")

    # Stream from file
    with open("audio.wav", "rb") as f:
        await client.transcribe(f, config)

asyncio.run(transcribe_realtime())
```

---

## WebSocket Client (Legacy)

```python
from speechmatics.models import ServerMessageType, TranscriptionConfig
from speechmatics.client import WebsocketClient

API_KEY = "YOUR_API_KEY"
PATH_TO_FILE = "audio.wav"

# Create client
client = WebsocketClient(API_KEY)

# Register event handlers
client.add_event_handler(
    event_name=ServerMessageType.AddPartialTranscript,
    event_handler=lambda msg: print(f"(PARTIAL) {msg['metadata']['transcript']}")
)

client.add_event_handler(
    event_name=ServerMessageType.AddTranscript,
    event_handler=lambda msg: print(f"(FINAL) {msg['metadata']['transcript']}")
)

# Configure transcription
config = TranscriptionConfig(
    language="en",
    enable_partials=True,
    max_delay=5,
    enable_entities=True
)

# Run transcription
with open(PATH_TO_FILE, "rb") as f:
    client.run_synchronously(f, config)
```

---

## Real-Time Message Flow

```
┌──────────────┐                              ┌──────────────────┐
│    CLIENT    │                              │   SPEECHMATICS   │
└──────┬───────┘                              └────────┬─────────┘
       │                                               │
       │  ─────── WebSocket Connect ───────▶          │
       │                                               │
       │  ─────── StartRecognition ────────▶          │
       │           (config, audio format)              │
       │                                               │
       │  ◀─────── RecognitionStarted ─────           │
       │                                               │
       │  ═══════ Audio Chunks (binary) ═══▶          │
       │                                               │
       │  ◀─────── AudioAdded (ack) ───────           │
       │                                               │
       │  ◀─────── AddPartialTranscript ───           │
       │           (interim results)                   │
       │                                               │
       │  ◀─────── AddTranscript ──────────           │
       │           (final results)                     │
       │                                               │
       │  ─────── EndOfStream ─────────────▶          │
       │                                               │
       │  ◀─────── EndOfTranscript ────────           │
       │                                               │
```

---

## Real-Time Configuration Options

```python
from speechmatics.models import TranscriptionConfig

config = TranscriptionConfig(
    # Language
    language="en",                    # ISO language code

    # Partials & Timing
    enable_partials=True,             # Enable interim results
    max_delay=5.0,                    # Max delay before forcing result

    # Features
    enable_entities=True,             # Named entity recognition
    diarization="speaker",            # Speaker identification
    operating_point="enhanced",       # "standard" or "enhanced" accuracy

    # Domain-specific
    domain="finance",                 # "finance", "medical", etc.

    # Custom vocabulary
    additional_vocab=[
        {"content": "Speechmatics", "sounds_like": ["speech matics"]},
        {"content": "API"}
    ],

    # Output
    output_locale="en-US",            # Formatting locale
    punctuation_sensitivity=0.5       # 0.0 to 1.0
)
```

---

## Sources

- [Real-time API Reference](https://docs.speechmatics.com/rt-api-ref)
- [Speechmatics Documentation](https://docs.speechmatics.com/)
- [Speechmatics Python SDK (GitHub)](https://github.com/speechmatics/speechmatics-python-sdk)
