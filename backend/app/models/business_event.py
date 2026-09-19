from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, generate_uuid, utc_now


class EventType(str, enum.Enum):
    SALES_DECLINE = "SALES_DECLINE"
    DEMAND_SPIKE = "DEMAND_SPIKE"
    STOCKOUT_RISK = "STOCKOUT_RISK"
    CUSTOMER_RISK = "CUSTOMER_RISK"
    GROWTH_OPPORTUNITY = "GROWTH_OPPORTUNITY"


class EventSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BusinessEvent(Base):
    __tablename__ = "business_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(SQLEnum(EventType, native_enum=False), nullable=False, index=True)
    severity = Column(SQLEnum(EventSeverity, native_enum=False), nullable=False, default=EventSeverity.MEDIUM)
    source = Column(String(100), nullable=False, default="rule_engine")
    payload = Column(JSON, nullable=False, default=dict)
    detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    processed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    merchant = relationship("Merchant", back_populates="business_events")
    recommendations = relationship("Recommendation", back_populates="business_event")

    def __repr__(self):
        return f"<BusinessEvent(id='{self.id}', event_type='{self.event_type}', severity='{self.severity}')>"
