"""
Paytm Pulse - Phase 7 Sarvam AI Client
Handles HTTP calls to Sarvam AI for Speech-to-Text and Text-to-Speech with full mock mode fallback.
"""

import os
import io
import base64
import logging
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("paytm_pulse.voice.sarvam")

SARVAM_BASE_URL = "https://api.sarvam.ai"


class SarvamClient:
    """
    Client for Sarvam AI speech platform (Indian Language AI models).
    Supports Kannada (kn-IN), Hindi (hi-IN), English (en-IN), Telugu (te-IN), Tamil (ta-IN), etc.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        mock_mode: Optional[bool] = None,
    ):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "").strip()
        env_mock = os.getenv("SARVAM_MOCK_MODE", "false").lower() in ("true", "1", "yes")
        if mock_mode is not None:
            self.mock_mode = mock_mode
        else:
            self.mock_mode = env_mock or not bool(self.api_key)

        self.headers = {
            "api-subscription-key": self.api_key,
        }

    def speech_to_text(
        self,
        audio_bytes: bytes,
        language_code: str = "kn-IN",
        model: str = "saarika:v2"
    ) -> Dict[str, Any]:
        """
        Transcribes audio binary into text using Sarvam STT API.
        """
        if self.mock_mode:
            logger.info(f"[SARVAM MOCK] Transcribing audio ({len(audio_bytes)} bytes, lang={language_code})")
            # Return realistic simulated transcription based on language
            mock_transcripts = {
                "kn-IN": "ಇವತ್ತು ನನ್ನ ಅಂಗಡಿಯ sales ಹೇಗಿದೆ?",
                "hi-IN": "आज मेरी दुकान की बिक्री कैसी है?",
                "en-IN": "How are my sales today?",
            }
            transcript = mock_transcripts.get(language_code, "How are my sales today?")
            return {
                "transcript": transcript,
                "language_code": language_code,
                "confidence": 0.96,
                "is_mock": True
            }

        try:
            files = {
                "file": ("audio.wav", audio_bytes, "audio/wav")
            }
            data = {
                "language_code": language_code,
                "model": model,
            }
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    f"{SARVAM_BASE_URL}/speech-to-text",
                    headers=self.headers,
                    data=data,
                    files=files
                )
                resp.raise_for_status()
                res_data = resp.json()
                return {
                    "transcript": res_data.get("transcript", ""),
                    "language_code": res_data.get("language_code", language_code),
                    "confidence": res_data.get("confidence", 0.95),
                    "is_mock": False
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"Sarvam STT HTTP error {e.response.status_code}: {e.response.text}")
            # Graceful fallback to mock response so pipeline never breaks completely
            return {
                "transcript": "How are my sales today?",
                "language_code": language_code,
                "confidence": 0.5,
                "is_mock": True,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Failed to execute Sarvam STT: {str(e)}", exc_info=True)
            return {
                "transcript": "How are my sales today?",
                "language_code": language_code,
                "confidence": 0.5,
                "is_mock": True,
                "error": str(e)
            }

    def text_to_speech(
        self,
        text: str,
        target_language_code: str = "kn-IN",
        speaker: str = "meera",
        pace: float = 1.0,
        model: str = "bulbul:v1"
    ) -> Dict[str, Any]:
        """
        Synthesizes text into Indian-language audio speech using Sarvam TTS.
        """
        if self.mock_mode:
            logger.info(f"[SARVAM MOCK] Synthesizing TTS: '{text[:40]}...' (lang={target_language_code})")
            # Generate dummy base64 audio payload
            dummy_audio_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
            b64_audio = base64.b64encode(dummy_audio_bytes).decode("utf-8")
            return {
                "audio_base64": b64_audio,
                "audio_url": "https://paytm-pulse.internal/mock-audio/response.wav",
                "language_code": target_language_code,
                "is_mock": True
            }

        try:
            payload = {
                "inputs": [text],
                "target_language_code": target_language_code,
                "speaker": speaker,
                "pitch": 0.0,
                "pace": pace,
                "loudness": 1.0,
                "speech_sample_rate": 22050,
                "enable_preprocessing": True,
                "model": model
            }
            with httpx.Client(timeout=20.0) as client:
                headers = {**self.headers, "Content-Type": "application/json"}
                resp = client.post(
                    f"{SARVAM_BASE_URL}/text-to-speech",
                    headers=headers,
                    json=payload
                )
                resp.raise_for_status()
                res_data = resp.json()
                audios = res_data.get("audios", [])
                audio_b64 = audios[0] if audios else None
                return {
                    "audio_base64": audio_b64,
                    "audio_url": None,
                    "language_code": target_language_code,
                    "is_mock": False
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"Sarvam TTS HTTP error {e.response.status_code}: {e.response.text}")
            return {
                "audio_base64": None,
                "audio_url": None,
                "language_code": target_language_code,
                "is_mock": True,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Failed to execute Sarvam TTS: {str(e)}", exc_info=True)
            return {
                "audio_base64": None,
                "audio_url": None,
                "language_code": target_language_code,
                "is_mock": True,
                "error": str(e)
            }

    def translate(
        self,
        input_text: str,
        target_language_code: str = "hi-IN",
        source_language_code: str = "en-IN",
        speaker_gender: str = "Male",
        mode: str = "formal",
        model: str = "mayura:v1"
    ) -> Dict[str, Any]:
        """
        Translates text across 10+ Indian languages using Sarvam AI Mayura Translation model.
        Supports hi-IN, kn-IN, te-IN, ta-IN, bn-IN, gu-IN, mr-IN, pa-IN, ml-IN, od-IN, en-IN.
        """
        if not input_text or target_language_code == source_language_code:
            return {
                "translated_text": input_text,
                "source_language_code": source_language_code,
                "target_language_code": target_language_code,
                "is_mock": False
            }

        if self.mock_mode:
            logger.info(f"[SARVAM MOCK] Translating ({source_language_code} -> {target_language_code}): '{input_text[:40]}...'")
            return {
                "translated_text": input_text,
                "source_language_code": source_language_code,
                "target_language_code": target_language_code,
                "is_mock": True
            }

        try:
            payload = {
                "input": input_text,
                "source_language_code": source_language_code,
                "target_language_code": target_language_code,
                "speaker_gender": speaker_gender,
                "mode": mode,
                "model": model,
                "enable_preprocessing": True
            }
            headers = {**self.headers, "Content-Type": "application/json"}
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(
                    f"{SARVAM_BASE_URL}/translate",
                    headers=headers,
                    json=payload
                )
                resp.raise_for_status()
                res_data = resp.json()
                translated = res_data.get("translated_text", input_text)
                return {
                    "translated_text": translated,
                    "source_language_code": source_language_code,
                    "target_language_code": target_language_code,
                    "is_mock": False
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"Sarvam Translate HTTP error {e.response.status_code}: {e.response.text}")
            return {
                "translated_text": input_text,
                "source_language_code": source_language_code,
                "target_language_code": target_language_code,
                "is_mock": True,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Failed to execute Sarvam Translation: {str(e)}", exc_info=True)
            return {
                "translated_text": input_text,
                "source_language_code": source_language_code,
                "target_language_code": target_language_code,
                "is_mock": True,
                "error": str(e)
            }


sarvam_client = SarvamClient()
