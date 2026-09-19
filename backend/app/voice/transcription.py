"""
Paytm Pulse - Phase 7 Voice Transcription
Handles audio transcription from raw bytes/media, language mapping, and fallback logic.
"""

import logging
from typing import Optional
from app.voice.sarvam_client import sarvam_client
from app.voice.schemas import TranscriptionResponse

logger = logging.getLogger("paytm_pulse.voice.transcription")

# Mapping merchant language names to Sarvam language codes
LANGUAGE_MAP = {
    "kannada": "kn-IN",
    "hindi": "hi-IN",
    "english": "en-IN",
    "tamil": "ta-IN",
    "telugu": "te-IN",
    "bengali": "bn-IN",
    "marathi": "mr-IN",
    "gujarati": "gu-IN",
}


def map_language_to_code(language_name: Optional[str]) -> str:
    """Maps merchant profile language name (e.g. 'Kannada', 'Hindi') to BCP 47 code (e.g. 'kn-IN')."""
    if not language_name:
        return "kn-IN"
    return LANGUAGE_MAP.get(language_name.lower().strip(), "kn-IN")


def transcribe_audio(
    audio_bytes: bytes,
    preferred_language: Optional[str] = "Kannada"
) -> TranscriptionResponse:
    """
    Transcribes incoming audio bytes to text using Sarvam AI.
    """
    lang_code = map_language_to_code(preferred_language)
    res = sarvam_client.speech_to_text(audio_bytes=audio_bytes, language_code=lang_code)
    
    return TranscriptionResponse(
        transcript=res.get("transcript", ""),
        detected_language=res.get("language_code", lang_code),
        confidence=res.get("confidence", 0.95),
        is_mock=res.get("is_mock", False)
    )
