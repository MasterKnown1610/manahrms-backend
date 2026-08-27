"""
OpenAI voice helpers: Whisper STT and TTS for AI chat.
Uses the same OPENAI_API_KEY as the agentic chat.
"""
from __future__ import annotations

import base64
import logging
from io import BytesIO
from typing import Optional, Tuple

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# Whisper accepts these; browsers often send webm/ogg from MediaRecorder
_ALLOWED_AUDIO_EXTENSIONS = {
    ".webm",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".m4a",
    ".wav",
    ".ogg",
    ".flac",
    ".oga",
}

_CONTENT_TYPE_BY_FORMAT = {
    "mp3": "audio/mpeg",
    "opus": "audio/opus",
    "aac": "audio/aac",
    "flac": "audio/flac",
}

_ALLOWED_TTS_VOICES = frozenset(
    {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
)
_ALLOWED_TTS_FORMATS = frozenset(_CONTENT_TYPE_BY_FORMAT.keys())


class VoiceService:
    """Speech-to-text (Whisper) and text-to-speech (OpenAI TTS)."""

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured.")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.whisper_model = settings.OPENAI_WHISPER_MODEL
        self.tts_model = settings.OPENAI_TTS_MODEL
        self.default_voice = settings.OPENAI_TTS_VOICE
        self.default_format = settings.OPENAI_TTS_FORMAT

    @staticmethod
    def content_type_for_format(fmt: str) -> str:
        return _CONTENT_TYPE_BY_FORMAT.get(fmt, "audio/mpeg")

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "voice.webm",
        language: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio bytes to text via Whisper.
        Raises ValueError on empty/invalid input; other errors propagate.
        """
        if not audio_bytes:
            raise ValueError("Audio file is empty.")

        max_size = settings.MAX_VOICE_AUDIO_SIZE
        if len(audio_bytes) > max_size:
            raise ValueError(
                f"Audio file is too large. Maximum size is {max_size // (1024 * 1024)}MB."
            )

        safe_name = (filename or "voice.webm").strip() or "voice.webm"
        # Ensure Whisper gets an extension it recognizes
        lower = safe_name.lower()
        if not any(lower.endswith(ext) for ext in _ALLOWED_AUDIO_EXTENSIONS):
            safe_name = f"{safe_name}.webm"

        buf = BytesIO(audio_bytes)
        # Tuple form is reliable across openai SDK versions (filename + fileobj)
        kwargs = {
            "model": self.whisper_model,
            "file": (safe_name, buf),
        }
        if language and language.strip():
            # ISO-639-1, e.g. en, te
            kwargs["language"] = language.strip()[:8]

        result = self.client.audio.transcriptions.create(**kwargs)
        text = (getattr(result, "text", None) or "").strip()
        return text

    def speak(
        self,
        text: str,
        voice: Optional[str] = None,
        audio_format: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """
        Convert text to speech.
        Returns (audio_base64, format, content_type).
        """
        cleaned = (text or "").strip()
        if not cleaned:
            raise ValueError("Text is required for speech.")

        # OpenAI TTS has practical length limits; truncate politely
        max_chars = 4096
        if len(cleaned) > max_chars:
            cleaned = cleaned[: max_chars - 3] + "..."

        use_voice = (voice or self.default_voice or "alloy").strip().lower()
        if use_voice not in _ALLOWED_TTS_VOICES:
            use_voice = "alloy"

        use_format = (audio_format or self.default_format or "mp3").strip().lower()
        if use_format not in _ALLOWED_TTS_FORMATS:
            use_format = "mp3"

        response = self.client.audio.speech.create(
            model=self.tts_model,
            voice=use_voice,
            input=cleaned,
            response_format=use_format,
        )

        # openai 1.x returns HttpxBinaryResponseContent (.content / .read())
        audio_bytes = getattr(response, "content", None)
        if audio_bytes is None and hasattr(response, "read"):
            audio_bytes = response.read()
        if not audio_bytes:
            raise ValueError("TTS returned empty audio.")

        b64 = base64.b64encode(audio_bytes).decode("ascii")
        content_type = self.content_type_for_format(use_format)
        return b64, use_format, content_type
