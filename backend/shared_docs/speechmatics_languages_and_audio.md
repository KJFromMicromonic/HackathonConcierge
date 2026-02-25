# Speechmatics — Supported Languages and Audio Formats

Comprehensive reference for Speechmatics language support (55+ languages) and audio format compatibility for both real-time and batch processing.

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

## Sources

- [Speechmatics Languages](https://docs.speechmatics.com/introduction/supported-languages)
- [Speechmatics Documentation](https://docs.speechmatics.com/)
