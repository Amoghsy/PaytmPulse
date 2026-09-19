"""
Paytm Pulse - Phase 7 WhatsApp Schemas
Pydantic data models for WhatsApp Cloud API payloads, webhooks, and interactive message elements.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class WhatsAppQuickReplyButton(BaseModel):
    id: str = Field(..., description="Unique ID / payload for the button, e.g. 'APPROVE_rec_123'")
    title: str = Field(..., description="Button display title")



class WhatsAppInteractiveAction(BaseModel):
    buttons: List[Dict[str, Any]] = Field(default_factory=list)


class WhatsAppInteractiveBody(BaseModel):
    text: str


class WhatsAppInteractiveHeader(BaseModel):
    type: str = "text"
    text: str


class WhatsAppInteractiveFooter(BaseModel):
    text: str


class WhatsAppInteractivePayload(BaseModel):
    type: str = "button"
    header: Optional[WhatsAppInteractiveHeader] = None
    body: WhatsAppInteractiveBody
    footer: Optional[WhatsAppInteractiveFooter] = None
    action: WhatsAppInteractiveAction


class SendMessageRequest(BaseModel):
    recipient_phone: str = Field(..., description="Recipient phone number with country code, e.g. '+919876543210'")
    message: str = Field(..., description="Plain text message content")
    preview_url: bool = False


class SendInteractiveMessageRequest(BaseModel):
    recipient_phone: str
    body_text: str
    buttons: List[WhatsAppQuickReplyButton]
    header_text: Optional[str] = None
    footer_text: Optional[str] = None


class SendAudioMessageRequest(BaseModel):
    recipient_phone: str
    audio_url: Optional[str] = None
    audio_data_base64: Optional[str] = None


class ParsedInboundMessage(BaseModel):
    message_id: str
    sender_phone: str
    timestamp: str
    message_type: str  # 'text', 'audio', 'interactive', 'button', 'unknown'
    text_content: Optional[str] = None
    audio_id: Optional[str] = None
    button_payload: Optional[str] = None
    button_title: Optional[str] = None
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
