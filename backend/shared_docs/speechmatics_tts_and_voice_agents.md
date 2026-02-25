# Speechmatics — Text-to-Speech and Voice Agents

Text-to-Speech (TTS) for converting text to natural-sounding speech, and Voice Agents for building conversational AI with intelligent turn detection.

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

## Sources

- [Speechmatics Documentation](https://docs.speechmatics.com/)
- [PyPI - speechmatics-tts](https://libraries.io/pypi/speechmatics-tts)
- [Speechmatics Python SDK (GitHub)](https://github.com/speechmatics/speechmatics-python-sdk)
