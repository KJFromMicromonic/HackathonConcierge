import asyncio
import io
from typing import Optional

from speechmatics.models import ConnectionSettings, TranscriptionConfig, ServerMessageType
from speechmatics.client import WebsocketClient
from speechmatics.tts import AsyncClient as TTSClient, Voice, OutputFormat

from app.config import get_settings


class SpeechmaticsService:
    """
    Speechmatics ASR (speech-to-text) and TTS (text-to-speech) integration.

    Uses:
    - speechmatics-python for ASR (WebsocketClient)
    - speechmatics-tts for TTS
    """

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.speechmatics_api_key
        self._tts_client: Optional[TTSClient] = None

    def _get_connection_settings(self) -> ConnectionSettings:
        return ConnectionSettings(
            url="wss://eu2.rt.speechmatics.com/v2",
            auth_token=self.api_key
        )

    @property
    def tts_client(self) -> TTSClient:
        if self._tts_client is None:
            self._tts_client = TTSClient(api_key=self.api_key)
        return self._tts_client

    async def transcribe(self, audio_data: bytes, language: str = "en") -> str:
        """
        Transcribe audio to text using Speechmatics ASR.

        Args:
            audio_data: Raw audio bytes (WAV format recommended)
            language: ISO language code (default: "en")

        Returns:
            Transcribed text
        """
        transcripts = []

        # Create client
        ws = WebsocketClient(self._get_connection_settings())

        # Set up event handlers
        ws.add_event_handler(
            event_name=ServerMessageType.AddTranscript,
            event_handler=lambda msg: transcripts.append(msg["metadata"]["transcript"])
        )

        # Configure transcription
        config = TranscriptionConfig(
            language=language,
            enable_partials=False,
            max_delay=2.0
        )

        # Run transcription synchronously (in a thread for async context)
        def run_transcription():
            audio_stream = io.BytesIO(audio_data)
            ws.run_synchronously(audio_stream, config)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_transcription)

        return " ".join(transcripts).strip()

    async def synthesize(self, text: str, voice: str = "en-GB-female-1") -> bytes:
        """
        Convert text to speech using Speechmatics TTS.

        Args:
            text: Text to synthesize
            voice: Voice model

        Returns:
            Audio bytes (WAV format)
        """
        response = await self.tts_client.synthesize(
            text=text,
            voice=voice,
            output_format=OutputFormat.WAV
        )
        return await response.read()

    async def close(self):
        """Clean up resources."""
        self._tts_client = None
