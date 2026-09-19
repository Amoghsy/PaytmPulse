from sqlalchemy import Column, String, Numeric, Text, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, generate_uuid, utc_now


class RecommendationType(str, enum.Enum):
    STOCK_REORDER = "STOCK_REORDER"
    SALES_RECOVERY = "SALES_RECOVERY"
    CUSTOMER_WINBACK = "CUSTOMER_WINBACK"
    PROMOTION = "PROMOTION"
    GROWTH_OPPORTUNITY = "GROWTH_OPPORTUNITY"
    FINANCIAL_PRODUCT = "FINANCIAL_PRODUCT"


class RecommendationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(36), ForeignKey("business_events.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(SQLEnum(RecommendationType, native_enum=False), nullable=False)
    title = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    confidence = Column(Numeric(3, 2), nullable=False, default=0.90)
    urgency = Column(String(20), nullable=False, default="MEDIUM")
    expected_impact = Column(Text, nullable=True)
    status = Column(SQLEnum(RecommendationStatus, native_enum=False), nullable=False, default=RecommendationStatus.PENDING, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    merchant = relationship("Merchant", back_populates="recommendations")
    business_event = relationship("BusinessEvent", back_populates="recommendations")
    actions = relationship("Action", back_populates="recommendation")

    def __repr__(self):
        return f"<Recommendation(id='{self.id}', type='{self.type}', status='{self.status}')>"
