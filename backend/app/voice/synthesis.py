"""
Paytm Pulse - Phase 7 Voice Synthesis
Handles Text-to-Speech audio generation for merchant voice responses.
"""

import logging
from typing import Optional
from app.voice.sarvam_client import sarvam_client
from app.voice.transcription import map_language_to_code
from app.voice.schemas import SpeechSynthesisResponse

logger = logging.getLogger("paytm_pulse.voice.synthesis")


def synthesize_speech(
    text: str,
    preferred_language: Optional[str] = "Kannada",
    speaker: str = "meera",
    pace: float = 1.0
) -> SpeechSynthesisResponse:
    """
    Synthesizes response text into natural voice audio for merchant reply.
    """
    lang_code = map_language_to_code(preferred_language)
    res = sarvam_client.text_to_speech(
        text=text,
        target_language_code=lang_code,
        speaker=speaker,
        pace=pace
    )

    return SpeechSynthesisResponse(
        audio_base64=res.get("audio_base64"),
        audio_url=res.get("audio_url"),
        language_code=lang_code,
        is_mock=res.get("is_mock", False)
    )
