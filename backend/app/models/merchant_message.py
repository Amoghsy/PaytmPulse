import enum
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Text, func
from app.models.base import Base, generate_uuid, utc_now


class MessageDirection(str, enum.Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class MessageType(str, enum.Enum):
    TEXT = "TEXT"
    VOICE = "VOICE"
    INTERACTIVE = "INTERACTIVE"
    BUTTON = "BUTTON"
    ALERT = "ALERT"
    TEMPLATE = "TEMPLATE"
    SYSTEM = "SYSTEM"


class MessageStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    QUEUED = "QUEUED"


class MerchantMessage(Base):
    __tablename__ = "merchant_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), nullable=False, index=True)
    direction = Column(SQLEnum(MessageDirection, native_enum=False), nullable=False)
    message_type = Column(SQLEnum(MessageType, native_enum=False), nullable=False, default=MessageType.TEXT)
    external_message_id = Column(String(255), nullable=True, index=True)
    sender_phone = Column(String(50), nullable=True)
    recipient_phone = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)
    status = Column(SQLEnum(MessageStatus, native_enum=False), nullable=False, default=MessageStatus.SENT)
    language = Column(String(20), nullable=True, default="en")
    extra_metadata = Column(Text, nullable=True)  # JSON encoded metadata
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<MerchantMessage(id='{self.id}', merchant_id='{self.merchant_id}', direction='{self.direction}', type='{self.message_type}')>"
