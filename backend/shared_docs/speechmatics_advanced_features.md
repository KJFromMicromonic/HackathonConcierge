# Speechmatics — Advanced Features

Advanced ASR features including speaker diarization, custom vocabulary, entity recognition, translation, audio intelligence, and domain-specific models.

---

## Speaker Diarization

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

---

## Custom Vocabulary

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

---

## Entity Recognition

Extract named entities:

```python
config = TranscriptionConfig(
    language="en",
    enable_entities=True
    # Detects: dates, times, currencies, percentages, etc.
)
```

---

## Translation

Real-time translation to 30+ languages:

```python
config = TranscriptionConfig(
    language="en",
    translation_config={
        "target_languages": ["es", "fr", "de"]
    }
)
```

---

## Audio Intelligence (Batch)

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

---

## Domain-Specific Models

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

## Sources

- [Speechmatics Documentation](https://docs.speechmatics.com/)
- [Real-time API Reference](https://docs.speechmatics.com/rt-api-ref)
- [Batch API Reference](https://docs.speechmatics.com/jobsapi)
