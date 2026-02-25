# Speechmatics — Examples, Error Handling, and Reference

Error handling, deployment options, integration examples (LiveKit, Twilio, Pipecat), a complete voice AI pipeline example, CLI reference, and quick reference tables.

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
