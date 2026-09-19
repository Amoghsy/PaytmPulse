"""
Paytm Pulse - Phase 7 Communication Schemas
Pydantic models for merchant interaction, message routing, test harnesses, and logs.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TestMessageRequest(BaseModel):
    merchant_id: Optional[str] = Field(None, description="Target merchant ID (optional if phone is provided)")
    phone: Optional[str] = Field(None, description="Merchant phone number, e.g. '9876543210'")
    message: str = Field(..., description="Message text or voice transcript, e.g. 'How are my sales today?'")
    is_voice: bool = Field(False, description="Simulate as voice message")
    language: Optional[str] = Field(None, description="Language preference override (e.g. 'Kannada', 'Hindi', 'English')")


class TestMessageResponse(BaseModel):
    merchant_id: str
    merchant_name: str
    shop_name: str
    input_message: str
    is_voice: bool
    response_text: str
    voice_audio_base64: Optional[str] = None
    voice_audio_url: Optional[str] = None
    intent_category: str
    suggested_action: Optional[str] = None
    whatsapp_sent: bool = True
    cooldown_active: bool = False


class TestRecommendationAlertRequest(BaseModel):
    decision_id: str = Field(..., description="Decision / Recommendation ID to generate proactive notification for")


class ProactiveAlertResponse(BaseModel):
    decision_id: str
    merchant_id: str
    alert_type: str
    message_text: str
    whatsapp_message_id: Optional[str] = None
    cooldown_prevented: bool = False
    status: str


class MerchantMessageLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    merchant_id: str
    direction: str
    message_type: str
    content: str
    status: str
    language: Optional[str] = None
    created_at: datetime
