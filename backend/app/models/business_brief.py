import enum
from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, utc_now


class BriefGenerationSource(str, enum.Enum):
    GEMINI = "gemini"
    FALLBACK = "fallback"


class BusinessBrief(Base):
    __tablename__ = "business_briefs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    brief_date = Column(String(10), nullable=False, index=True)  # Format: YYYY-MM-DD
    headline = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    content = Column(JSON, nullable=False, default=dict)  # Full structured JSON output
    generated_by = Column(String(50), nullable=False, default=BriefGenerationSource.GEMINI.value)
    language = Column(String(20), nullable=False, default="en")
    dashboard_delivered = Column(Boolean, nullable=False, default=True)
    whatsapp_delivered = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Idempotency constraint: 1 brief per merchant per calendar day
    __table_args__ = (
        UniqueConstraint("merchant_id", "brief_date", name="uq_merchant_brief_date"),
    )

    # Relationship
    merchant = relationship("Merchant")

    def __repr__(self):
        return f"<BusinessBrief(id='{self.id}', merchant_id='{self.merchant_id}', date='{self.brief_date}', source='{self.generated_by}')>"
