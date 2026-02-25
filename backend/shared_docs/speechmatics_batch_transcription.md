# Speechmatics — Batch Transcription

Batch (asynchronous) transcription for processing audio files. Submit jobs and retrieve results when ready.

**Package:** `pip install speechmatics-batch`

---

## Simple Example

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

---

## Full Job Control

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

---

## Synchronous Batch Client

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

---

## Batch API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/jobs` | POST | Create a new transcription job |
| `/jobs` | GET | List all jobs |
| `/jobs/{id}` | GET | Get job status |
| `/jobs/{id}` | DELETE | Cancel/delete job |
| `/jobs/{id}/transcript` | GET | Get transcription result |

---

## Batch Status Codes

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

## Sources

- [Batch API Reference](https://docs.speechmatics.com/jobsapi)
- [Speechmatics Documentation](https://docs.speechmatics.com/)
- [PyPI - speechmatics-batch](https://pypi.org/project/speechmatics-batch/)
