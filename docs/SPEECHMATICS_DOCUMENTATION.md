# Speechmatics Documentation

A comprehensive guide to the Speechmatics platform - enterprise-grade Speech-to-Text (ASR), Text-to-Speech (TTS), and Voice AI Agent APIs.

**Languages:** 55+ languages supported
**License:** MIT (SDK)
**Python:** 3.8+
**Website:** [speechmatics.com](https://www.speechmatics.com)
**Docs:** [docs.speechmatics.com](https://docs.speechmatics.com)

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Authentication](#authentication)
4. [Speech-to-Text (ASR)](#speech-to-text-asr)
   - [Real-Time Streaming](#real-time-streaming)
   - [Batch Transcription](#batch-transcription)
5. [Text-to-Speech (TTS)](#text-to-speech-tts)
6. [Voice Agents](#voice-agents)
7. [Supported Languages](#supported-languages)
8. [Audio Formats](#audio-formats)
9. [Advanced Features](#advanced-features)
10. [Error Handling](#error-handling)
11. [Deployment Options](#deployment-options)
12. [Integration Examples](#integration-examples)
13. [Complete Pipeline Example](#complete-pipeline-example)

---

## Overview

Speechmatics provides a complete voice AI platform with three core capabilities:

| Capability | Description | Latency |
|------------|-------------|---------|
| **ASR (Speech-to-Text)** | Convert audio to text | ~150ms (real-time) |
| **TTS (Text-to-Speech)** | Convert text to audio | ~150ms first byte |
| **Voice Agents** | Conversational AI with turn detection | Real-time |

### Key Differentiators

- **55+ Languages** with accent/dialect support
- **Ultra-low latency** (150ms p95)
- **Speaker Diarization** - identify who said what
- **Domain-specific models** - Medical, Finance
- **Flexible deployment** - Cloud, On-prem, Edge

---

## Installation

Speechmatics offers modular packages for different use cases:

```bash
# Real-time streaming transcription
pip install speechmatics-rt

# Batch/async transcription
pip install speechmatics-batch

# Text-to-Speech
pip install speechmatics-tts

# Voice Agents
pip install speechmatics-voice

# Legacy all-in-one (deprecated Dec 2025)
pip install speechmatics-python
```

### Package Comparison

| Package | Use Case | Async | Sync |
|---------|----------|-------|------|
| `speechmatics-rt` | Live audio streams | Yes | Yes |
| `speechmatics-batch` | File transcription | Yes | No |
| `speechmatics-tts` | Speech synthesis | Yes | No |
| `speechmatics-voice` | Voice AI agents | Yes | No |

---

## Authentication

Get your API key from [portal.speechmatics.com](https://portal.speechmatics.com).

### Environment Variable (Recommended)

```bash
# .env file
SPEECHMATICS_API_KEY=your_api_key_here
```

```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("SPEECHMATICS_API_KEY")
```

### JWT Authentication (Enhanced Security)

For browser or short-lived sessions:

```python
from speechmatics.batch import AsyncClient, JWTAuth

# Auto-refreshing JWT tokens
auth = JWTAuth("your-api-key", ttl=60)  # 60 second TTL

async with AsyncClient(auth=auth) as client:
    result = await client.transcribe("audio.wav")
```

### CLI Configuration

```bash
# Set API key globally
speechmatics config set --auth-token YOUR_API_KEY

# Configure endpoints
speechmatics config set --rt-url wss://eu.rt.speechmatics.com/v2
speechmatics config set --batch-url https://eu1.asr.api.speechmatics.com/v2

# Settings stored in ~/.speechmatics/config (TOML format)
```

---

## Speech-to-Text (ASR)

Speechmatics ASR converts audio to text with two modes: **Real-Time Streaming** and **Batch Processing**.

### Real-Time Streaming

For live audio with ultra-low latency (~150ms).

#### Basic Example

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

#### WebSocket Client (Legacy)

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

#### Real-Time Message Flow

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

#### Real-Time Configuration Options

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

### Batch Transcription

For processing audio files asynchronously.

#### Simple Example

```python
import asyncio
from speechmatics.batch import AsyncClient, TranscriptionConfig

async def transcribe_file():
    async with AsyncClient(api_key="YOUR_API_KEY") as client:
        result = await client.transcribe(
            "meeting.mp3",
            transcription_config=TranscriptionConfig(language="en")
        )
        print(result.transcript_text)

asyncio.run(transcribe_file())
```

#### Full Job Control

```python
import asyncio
from speechmatics.batch import AsyncClient, JobConfig, JobType, TranscriptionConfig

async def batch_with_job_control():
    async with AsyncClient(api_key="YOUR_API_KEY") as client:

        # Configure job
        config = JobConfig(
            type=JobType.TRANSCRIPTION,
            transcription_config=TranscriptionConfig(
                language="en",
                operating_point="enhanced",
                diarization="speaker",
                enable_entities=True
            )
        )

        # Submit job
        job = await client.submit_job("recording.wav", config=config)
        print(f"Job ID: {job.id}")

        # Wait for completion
        result = await client.wait_for_completion(
            job.id,
            polling_interval=2.0,  # Check every 2 seconds
            timeout=300.0          # 5 minute timeout
        )

        # Access results
        print(f"Transcript: {result.transcript_text}")
        print(f"Confidence: {result.confidence}")

        # Access speaker segments (if diarization enabled)
        for segment in result.segments:
            print(f"[{segment.speaker}] {segment.text}")

asyncio.run(batch_with_job_control())
```

#### Synchronous Batch Client

```python
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient

settings = ConnectionSettings(
    url="https://eu1.asr.api.speechmatics.com/v2",
    auth_token="YOUR_API_KEY"
)

config = {
    "type": "transcription",
    "transcription_config": {
        "language": "en",
        "operating_point": "enhanced",
        "diarization": "speaker"
    }
}

with BatchClient(settings) as client:
    # Submit job
    job_id = client.submit_job(
        audio="meeting.wav",
        transcription_config=config
    )
    print(f"Job {job_id} submitted")

    # Wait and get transcript
    transcript = client.wait_for_completion(
        job_id,
        transcription_format="txt"  # or "json-v2"
    )
    print(transcript)
```

#### Batch API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/jobs` | POST | Create a new transcription job |
| `/jobs` | GET | List all jobs |
| `/jobs/{id}` | GET | Get job status |
| `/jobs/{id}` | DELETE | Cancel/delete job |
| `/jobs/{id}/transcript` | GET | Get transcription result |

#### Batch Status Codes

| Code | Description |
|------|-------------|
| 201 | Job created successfully |
| 400 | Invalid request parameters |
| 401 | Invalid authentication |
| 403 | Insufficient permissions |
| 410 | Resource no longer available |
| 429 | Rate limit exceeded |
| 500 | Server error |

---

## Text-to-Speech (TTS)

Convert text to natural-sounding speech.

### Installation

```bash
pip install speechmatics-tts
```

### Basic Usage

```python
import asyncio
from speechmatics.tts import AsyncClient, Voice, OutputFormat

async def text_to_speech():
    client = AsyncClient(api_key="YOUR_API_KEY")

    response = await client.generate(
        text="Hello! Welcome to Speechmatics Text-to-Speech.",
        voice=Voice.SARAH,
        output_format=OutputFormat.WAV_16000
    )

    # Get audio bytes
    audio_data = await response.read()

    # Save to file
    with open("output.wav", "wb") as f:
        f.write(audio_data)

    await client.close()

asyncio.run(text_to_speech())
```

### Streaming TTS

```python
async def stream_tts():
    client = AsyncClient(api_key="YOUR_API_KEY")

    async for audio_chunk in client.stream(
        text="This is a longer piece of text that will be streamed.",
        voice=Voice.SARAH
    ):
        # Process audio chunks as they arrive
        yield audio_chunk

    await client.close()
```

### Available Voices

| Voice | Language | Gender |
|-------|----------|--------|
| `SARAH` | English (US) | Female |
| `JAMES` | English (US) | Male |
| `EMMA` | English (UK) | Female |
| `OLIVER` | English (UK) | Male |

### Output Formats

| Format | Sample Rate | Description |
|--------|-------------|-------------|
| `WAV_16000` | 16 kHz | Standard quality WAV |
| `WAV_22050` | 22.05 kHz | Higher quality WAV |
| `WAV_44100` | 44.1 kHz | CD quality WAV |
| `MP3` | Variable | Compressed audio |
| `OGG` | Variable | Ogg Vorbis |

---

## Voice Agents

Build conversational AI with intelligent turn detection.

### Installation

```bash
pip install speechmatics-voice
```

### Basic Voice Agent

```python
import asyncio
from speechmatics.voice import VoiceAgent, AgentConfig

async def voice_agent():
    config = AgentConfig(
        language="en",
        voice="sarah",
        turn_detection="smart",  # ML-based turn detection
        diarization=True
    )

    agent = VoiceAgent(api_key="YOUR_API_KEY", config=config)

    @agent.on("user_speech")
    def on_user_speech(text):
        print(f"User: {text}")

    @agent.on("turn_end")
    async def on_turn_end(transcript):
        # Process user input, get LLM response
        response = await get_llm_response(transcript)
        await agent.speak(response)

    await agent.start()

asyncio.run(voice_agent())
```

### Turn Detection Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `silence` | Silence-based (basic) | Simple commands |
| `smart` | ML-based intelligent | Natural conversation |
| `manual` | Explicit end signal | Push-to-talk |

### Speaker Features

```python
config = AgentConfig(
    # Speaker Diarization - identify different speakers
    diarization=True,

    # Speaker ID - recognize specific people
    speaker_identification=True,
    speaker_profiles=["user_1", "user_2"],

    # Speaker Focus - prioritize main speaker
    speaker_focus=True,
    prefer_current_speaker=True
)
```

---

## Supported Languages

Speechmatics supports 55+ languages with two accuracy tiers:

- **Standard**: Optimized for faster turnaround
- **Enhanced**: Highest accuracy model

### Language Codes

| Language | Code | Enhanced | Medical |
|----------|------|----------|---------|
| English | `en` | Yes | Yes |
| Spanish | `es` | Yes | Yes |
| French | `fr` | Yes | Yes |
| German | `de` | Yes | Yes |
| Italian | `it` | Yes | No |
| Portuguese | `pt` | Yes | No |
| Dutch | `nl` | Yes | Yes |
| Japanese | `ja` | Yes | No |
| Korean | `ko` | Yes | No |
| Mandarin | `cmn` | Yes | No |
| Arabic | `ar` | Yes | No |
| Hindi | `hi` | Yes | No |
| Russian | `ru` | Yes | No |
| Polish | `pl` | Yes | No |
| Turkish | `tr` | Yes | No |
| Swedish | `sv` | Yes | Yes |
| Norwegian | `no` | Yes | Yes |
| Danish | `da` | Yes | Yes |
| Finnish | `fi` | Yes | Yes |

### Bilingual Packs

For code-switching environments:

| Pack | Code | Description |
|------|------|-------------|
| Malay & English | `en_ms` | Southeast Asia |
| Mandarin & English | `cmn_en` | China/Taiwan |
| Tamil & English | `en_ta` | India/Singapore |
| Spanish & English | `es` + `domain='bilingual-en'` | Americas |
| Multi (CMN/MS/TA/EN) | `cmn_en_ms_ta` | Singapore |

### Translation Languages

Translation supported for 30+ languages. **Not supported** for:
Arabic, Bashkir, Belarusian, Welsh, Esperanto, Basque, Mongolian, Marathi, Tamil, Thai, Uyghur, Cantonese.

---

## Audio Formats

### Real-Time Supported Formats

**Raw Audio (headerless):**
| Encoding | Description |
|----------|-------------|
| `pcm_f32le` | PCM 32-bit float, little-endian |
| `pcm_s16le` | PCM 16-bit signed, little-endian |
| `mulaw` | μ-law encoding |

**File Formats (with headers):**
WAV, MP3, AAC, OGG, MPEG, AMR, M4A, MP4, FLAC

### Batch Supported Formats

All common audio/video formats including:
- Audio: WAV, MP3, FLAC, OGG, M4A, AAC, WMA
- Video: MP4, MOV, AVI, MKV, WebM

### Recommended Settings

```python
# Optimal for real-time streaming
audio_settings = {
    "encoding": "pcm_s16le",
    "sample_rate": 16000,
    "channels": 1  # Mono recommended
}
```

---

## Advanced Features

### Speaker Diarization

Identify who said what in multi-speaker audio.

```python
config = TranscriptionConfig(
    language="en",
    diarization="speaker",  # or "channel" for separate audio channels
    speaker_diarization_config={
        "max_speakers": 4,
        "prefer_current_speaker": True
    }
)
```

### Custom Vocabulary

Add domain-specific terms:

```python
config = TranscriptionConfig(
    language="en",
    additional_vocab=[
        {"content": "Speechmatics"},
        {"content": "HIPAA", "sounds_like": ["hippa", "hip a"]},
        {"content": "COVID-19", "sounds_like": ["covid nineteen"]}
    ]
)
```

### Entity Recognition

Extract named entities:

```python
config = TranscriptionConfig(
    language="en",
    enable_entities=True
    # Detects: dates, times, currencies, percentages, etc.
)
```

### Translation

Real-time translation to 30+ languages:

```python
config = TranscriptionConfig(
    language="en",
    translation_config={
        "target_languages": ["es", "fr", "de"]
    }
)
```

### Audio Intelligence (Batch)

```python
config = JobConfig(
    type=JobType.TRANSCRIPTION,
    transcription_config=TranscriptionConfig(language="en"),

    # Summarization
    summarization_config={"content_type": "informative"},

    # Sentiment Analysis
    sentiment_analysis_config={"enabled": True},

    # Topic Detection
    topic_detection_config={"enabled": True},

    # Auto Chapters
    auto_chapters_config={"enabled": True}
)
```

### Domain-Specific Models

```python
# Medical transcription
config = TranscriptionConfig(
    language="en",
    operating_point="enhanced",
    domain="medical"  # Optimized for medical terminology
)

# Finance
config = TranscriptionConfig(
    language="en",
    domain="finance"
)
```

---

## Error Handling

### WebSocket Error Codes

| Code | Description | Action |
|------|-------------|--------|
| 1008 | Timeout/Policy violation | Reconnect |
| 4001 | Invalid message | Check message format |
| 4002 | Authentication failed | Check API key |
| 4003 | Configuration error | Check config params |
| 4005 | Max connections reached | Wait and retry |

### HTTP Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid API key |
| 403 | Forbidden - Insufficient permissions |
| 429 | Rate Limited - Too many requests |
| 500 | Server Error - Retry with backoff |

### Retry Strategy

```python
import asyncio
from speechmatics.batch import AsyncClient

async def transcribe_with_retry(file_path, max_retries=3):
    for attempt in range(max_retries):
        try:
            async with AsyncClient(api_key="YOUR_API_KEY") as client:
                return await client.transcribe(file_path)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
```

---

## Deployment Options

Speechmatics offers flexible deployment:

| Option | Description | Use Case |
|--------|-------------|----------|
| **SaaS** | Cloud-hosted API | Most users |
| **On-Premises** | Self-hosted containers | Data privacy |
| **Air-Gapped** | Isolated network | High security |
| **Edge** | On-device | Low latency, offline |

### API Endpoints

| Region | Real-Time | Batch |
|--------|-----------|-------|
| EU | `wss://eu.rt.speechmatics.com/v2` | `https://eu1.asr.api.speechmatics.com/v2` |
| US | `wss://us.rt.speechmatics.com/v2` | `https://us1.asr.api.speechmatics.com/v2` |

---

## Integration Examples

### LiveKit Integration

```python
from livekit import agents
from speechmatics.voice import VoiceAgent

class SpeechmaticsPlugin(agents.Plugin):
    def __init__(self):
        self.agent = VoiceAgent(api_key="YOUR_KEY")

    async def process_audio(self, audio_frame):
        transcript = await self.agent.transcribe(audio_frame)
        return transcript
```

### Twilio Media Streams

```python
from fastapi import WebSocket
from speechmatics.rt import RealtimeClient

@app.websocket("/twilio/media")
async def twilio_media(websocket: WebSocket):
    await websocket.accept()

    client = RealtimeClient(api_key="YOUR_KEY")

    async for message in websocket.iter_json():
        if message["event"] == "media":
            audio = base64.b64decode(message["media"]["payload"])
            transcript = await client.transcribe_chunk(audio)
            # Process transcript...
```

### Pipecat AI

```python
from pipecat.frames import AudioFrame
from speechmatics.voice import VoiceAgent

class SpeechmaticsSTT:
    def __init__(self):
        self.client = VoiceAgent(api_key="YOUR_KEY")

    async def process_frame(self, frame: AudioFrame):
        if isinstance(frame, AudioFrame):
            text = await self.client.transcribe(frame.audio)
            yield TextFrame(text=text)
```

---

## Complete Pipeline Example

Full voice AI pipeline with Speechmatics ASR/TTS and an LLM:

```python
import asyncio
import os
from dotenv import load_dotenv
from speechmatics.rt import RealtimeClient, TranscriptionConfig
from speechmatics.tts import AsyncClient as TTSClient, Voice, OutputFormat

load_dotenv()

class VoiceAIPipeline:
    """Complete voice pipeline: ASR → LLM → TTS"""

    def __init__(self):
        self.api_key = os.getenv("SPEECHMATICS_API_KEY")
        self.asr_client = None
        self.tts_client = TTSClient(api_key=self.api_key)

    async def speech_to_text(self, audio_stream) -> str:
        """Real-time ASR: Audio → Text"""
        self.asr_client = RealtimeClient(api_key=self.api_key)

        config = TranscriptionConfig(
            language="en",
            enable_partials=True,
            max_delay=2.0,
            operating_point="enhanced"
        )

        full_transcript = []

        @self.asr_client.on("final_transcript")
        def on_final(msg):
            full_transcript.append(msg['metadata']['transcript'])

        await self.asr_client.transcribe(audio_stream, config)

        return " ".join(full_transcript)

    async def text_to_speech(self, text: str) -> bytes:
        """TTS: Text → Audio"""
        response = await self.tts_client.generate(
            text=text,
            voice=Voice.SARAH,
            output_format=OutputFormat.WAV_16000
        )
        return await response.read()

    async def stream_tts(self, text: str):
        """Streaming TTS for lower latency"""
        async for chunk in self.tts_client.stream(
            text=text,
            voice=Voice.SARAH
        ):
            yield chunk

    async def process_conversation(self, audio_input: bytes, llm_callback) -> bytes:
        """
        Full pipeline:
        1. ASR: Audio → Text
        2. LLM: Text → Response
        3. TTS: Response → Audio
        """
        # Step 1: Speech to Text
        user_text = await self.speech_to_text(audio_input)
        print(f"User said: {user_text}")

        # Step 2: LLM Processing (your callback)
        ai_response = await llm_callback(user_text)
        print(f"AI response: {ai_response}")

        # Step 3: Text to Speech
        audio_output = await self.text_to_speech(ai_response)

        return audio_output

    async def close(self):
        await self.tts_client.close()


# Usage with Backboard LLM
async def main():
    from backboard import BackboardClient

    # Initialize clients
    pipeline = VoiceAIPipeline()
    backboard = BackboardClient(api_key=os.getenv("BACKBOARD_API_KEY"))

    # Create assistant and thread
    assistant = await backboard.create_assistant(name="Voice Assistant")
    thread = await backboard.create_thread(assistant.assistant_id)

    # LLM callback using Backboard
    async def llm_callback(user_text: str) -> str:
        response = await backboard.add_message(
            thread_id=thread.thread_id,
            content=user_text,
            llm_provider="openai",
            model_name="gpt-4o",
            memory="auto"
        )
        return response.content

    # Process voice conversation
    with open("user_audio.wav", "rb") as f:
        audio_input = f.read()

    audio_response = await pipeline.process_conversation(
        audio_input,
        llm_callback
    )

    # Save response
    with open("response.wav", "wb") as f:
        f.write(audio_response)

    # Cleanup
    await pipeline.close()
    await backboard.aclose()

asyncio.run(main())
```

### FastAPI WebSocket Server

```python
from fastapi import FastAPI, WebSocket
from speechmatics.rt import RealtimeClient, TranscriptionConfig
from speechmatics.tts import AsyncClient as TTSClient, Voice
import asyncio
import json

app = FastAPI()

@app.websocket("/voice")
async def voice_endpoint(websocket: WebSocket):
    await websocket.accept()

    asr = RealtimeClient(api_key="YOUR_KEY")
    tts = TTSClient(api_key="YOUR_KEY")

    config = TranscriptionConfig(
        language="en",
        enable_partials=True
    )

    @asr.on("partial_transcript")
    async def on_partial(msg):
        await websocket.send_json({
            "type": "partial",
            "text": msg['metadata']['transcript']
        })

    @asr.on("final_transcript")
    async def on_final(msg):
        text = msg['metadata']['transcript']
        await websocket.send_json({
            "type": "final",
            "text": text
        })

        # Get LLM response (your logic here)
        response_text = await get_llm_response(text)

        # Stream TTS back
        async for chunk in tts.stream(response_text, voice=Voice.SARAH):
            await websocket.send_bytes(chunk)

    try:
        async for message in websocket.iter_bytes():
            await asr.send_audio(message)
    finally:
        await asr.close()
        await tts.close()
```

---

## CLI Reference

### Real-Time Transcription

```bash
# Basic transcription
speechmatics transcribe --lang en audio.wav

# With streaming output
speechmatics transcribe --lang en --output-format json-v2 audio.wav

# From microphone (requires ffmpeg)
ffmpeg -f avfoundation -i ":0" -f wav - | speechmatics transcribe --lang en -

# With translation
speechmatics transcribe --lang en --translation-langs de,es audio.wav
```

### Batch Transcription

```bash
# Submit job
speechmatics batch transcribe --lang en recording.mp3

# With speaker diarization
speechmatics batch transcribe --lang en --diarization speaker meeting.wav

# With auto language detection
speechmatics batch transcribe --lang auto interview.mp3
```

---

## Quick Reference

### Package Installation

| Package | Command |
|---------|---------|
| Real-time | `pip install speechmatics-rt` |
| Batch | `pip install speechmatics-batch` |
| TTS | `pip install speechmatics-tts` |
| Voice | `pip install speechmatics-voice` |

### Key Classes

| Class | Package | Purpose |
|-------|---------|---------|
| `RealtimeClient` | speechmatics-rt | Live streaming ASR |
| `AsyncClient` | speechmatics-batch | Async file transcription |
| `AsyncClient` | speechmatics-tts | Text-to-speech |
| `VoiceAgent` | speechmatics-voice | Conversational AI |

### Configuration Objects

| Object | Purpose |
|--------|---------|
| `TranscriptionConfig` | ASR settings |
| `JobConfig` | Batch job settings |
| `AgentConfig` | Voice agent settings |

---

## Sources

- [Speechmatics Documentation](https://docs.speechmatics.com/)
- [Speechmatics Python SDK (GitHub)](https://github.com/speechmatics/speechmatics-python-sdk)
- [Speechmatics Academy](https://github.com/speechmatics/speechmatics-academy)
- [PyPI - speechmatics-batch](https://pypi.org/project/speechmatics-batch/)
- [PyPI - speechmatics-tts](https://libraries.io/pypi/speechmatics-tts)
- [Speechmatics Languages](https://docs.speechmatics.com/introduction/supported-languages)
- [Real-time API Reference](https://docs.speechmatics.com/rt-api-ref)
- [Batch API Reference](https://docs.speechmatics.com/jobsapi)
