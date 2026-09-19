import pytest
from app.voice.transcription import transcribe_audio, map_language_to_code
from app.voice.synthesis import synthesize_speech
from app.voice.sarvam_client import SarvamClient


def test_language_code_mapping():
    assert map_language_to_code("Kannada") == "kn-IN"
    assert map_language_to_code("Hindi") == "hi-IN"
    assert map_language_to_code("English") == "en-IN"
    assert map_language_to_code("kannada") == "kn-IN"
    assert map_language_to_code("UnknownLanguage") == "kn-IN"


def test_sarvam_mock_stt_transcription():
    client = SarvamClient(mock_mode=True)
    res = client.speech_to_text(b"mock_audio_bytes", language_code="kn-IN")
    assert res.get("is_mock") is True
    assert "sales" in res.get("transcript", "").lower() or len(res.get("transcript", "")) > 0


def test_sarvam_mock_tts_synthesis():
    client = SarvamClient(mock_mode=True)
    res = client.text_to_speech("Your sales are ₹15,000 today", target_language_code="kn-IN")
    assert res.get("is_mock") is True
    assert res.get("audio_base64") is not None


def test_transcribe_audio_helper():
    resp = transcribe_audio(b"sample_wav_bytes", preferred_language="Kannada")
    assert resp.detected_language == "kn-IN"
    assert resp.transcript != ""


def test_synthesize_speech_helper():
    resp = synthesize_speech("Cold drinks stock is low", preferred_language="Hindi")
    assert resp.language_code == "hi-IN"
    assert resp.audio_base64 is not None
