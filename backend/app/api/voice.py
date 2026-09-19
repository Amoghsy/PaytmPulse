"""
Paytm Pulse - Phase 7 Voice API Router
Exposes REST endpoints for Speech-to-Text transcription (Sarvam saarika:v2)
and Text-to-Speech voice synthesis (Sarvam bulbul:v1) with fallback.
"""

import logging
import base64
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel, Field

from app.voice.transcription import transcribe_audio
from app.voice.synthesis import synthesize_speech
from app.voice.schemas import TranscriptionResponse, SpeechSynthesisResponse

logger = logging.getLogger("paytm_pulse.api.voice")

router = APIRouter(tags=["Voice - STT & TTS (Sarvam AI)"])


class SynthesizePayload(BaseModel):
    text: str = Field(..., description="Text content to speak")
    language: Optional[str] = Field("English", description="Target language (English, Kannada, Hindi, Tamil, Telugu)")
    speaker: Optional[str] = Field("meera", description="Voice persona: meera or arvind")
    pace: Optional[float] = Field(1.0, description="Speech rate/pace")


class TranscribePayload(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded audio bytes")
    language: Optional[str] = Field("Kannada", description="Spoken language hint")


@router.post("/voice/synthesize", response_model=SpeechSynthesisResponse, status_code=status.HTTP_200_OK)
def synthesize_voice_endpoint(payload: SynthesizePayload):
    """
    Synthesizes text into high-quality Indian vernacular speech (WAV/MP3 audio) using Sarvam bulbul:v1.
    """
    if not payload.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text cannot be empty")
    try:
        res = synthesize_speech(
            text=payload.text,
            preferred_language=payload.language,
            speaker=payload.speaker,
            pace=payload.pace
        )
        return res
    except Exception as e:
        logger.error(f"Failed to synthesize voice: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Voice synthesis error: {str(e)}")


@router.post("/voice/transcribe", response_model=TranscriptionResponse, status_code=status.HTTP_200_OK)
def transcribe_voice_endpoint(payload: TranscribePayload):
    """
    Transcribes audio bytes (base64) into text using Sarvam saarika:v2.
    """
    try:
        audio_bytes = base64.b64decode(payload.audio_base64)
        res = transcribe_audio(
            audio_bytes=audio_bytes,
            preferred_language=payload.language
        )
        return res
    except Exception as e:
        logger.error(f"Failed to transcribe voice: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Voice transcription error: {str(e)}")


@router.post("/voice/transcribe-file", response_model=TranscriptionResponse, status_code=status.HTTP_200_OK)
async def transcribe_file_endpoint(
    file: UploadFile = File(...),
    language: Optional[str] = Form("Kannada")
):
    """
    Upload multipart audio file and transcribe into text.
    """
    try:
        audio_bytes = await file.read()
        res = transcribe_audio(
            audio_bytes=audio_bytes,
            preferred_language=language
        )
        return res
    except Exception as e:
        logger.error(f"Failed to transcribe uploaded audio file: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"File transcription error: {str(e)}")
