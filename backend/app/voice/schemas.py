"""
Paytm Pulse - Phase 7 Sarvam AI Voice Schemas
Pydantic data models for Speech-to-Text (STT) and Text-to-Speech (TTS).
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TranscriptionRequest(BaseModel):
    language_code: Optional[str] = Field("kn-IN", description="Language code e.g. 'kn-IN', 'hi-IN', 'en-IN'")
    model: str = Field("saarika:v2", description="Sarvam STT model name")


class TranscriptionResponse(BaseModel):
    transcript: str = Field(..., description="Transcribed text from speech")
    detected_language: Optional[str] = Field(None, description="Detected or requested language code")
    confidence: float = Field(0.95, description="Confidence score")
    is_mock: bool = False


class SpeechSynthesisRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize into speech")
    target_language_code: str = Field("kn-IN", description="Target language code, e.g. 'kn-IN', 'hi-IN', 'en-IN'")
    speaker: str = Field("meera", description="Voice speaker persona, e.g. 'meera', 'arvind'")
    pitch: float = Field(0.0, description="Pitch modification")
    pace: float = Field(1.0, description="Pace of speech")
    model: str = Field("bulbul:v1", description="Sarvam TTS model name")


class SpeechSynthesisResponse(BaseModel):
    audio_base64: Optional[str] = Field(None, description="Base64 encoded WAV/MP3 audio")
    audio_url: Optional[str] = Field(None, description="Accessible audio URL if uploaded/saved")
    language_code: str
    is_mock: bool = False
