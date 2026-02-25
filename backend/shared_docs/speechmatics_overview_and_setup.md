# Speechmatics — Overview and Setup

A comprehensive guide to getting started with the Speechmatics platform - enterprise-grade Speech-to-Text (ASR), Text-to-Speech (TTS), and Voice AI Agent APIs.

**Languages:** 55+ languages supported
**License:** MIT (SDK)
**Python:** 3.8+
**Website:** [speechmatics.com](https://www.speechmatics.com)
**Docs:** [docs.speechmatics.com](https://docs.speechmatics.com)

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

## Sources

- [Speechmatics Documentation](https://docs.speechmatics.com/)
- [Speechmatics Python SDK (GitHub)](https://github.com/speechmatics/speechmatics-python-sdk)
- [PyPI - speechmatics-batch](https://pypi.org/project/speechmatics-batch/)
- [PyPI - speechmatics-tts](https://libraries.io/pypi/speechmatics-tts)
