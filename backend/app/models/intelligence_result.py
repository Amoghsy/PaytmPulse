from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, utc_now


class IntelligenceResult(Base):
    __tablename__ = "intelligence_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(36), ForeignKey("business_events.id", ondelete="SET NULL"), nullable=True, index=True)
    result_type = Column(String(50), nullable=False, index=True)  # e.g., SALES_ANALYSIS, ANOMALY, DEMAND_FORECAST, STOCKOUT_RISK, CUSTOMER_RFM, OPPORTUNITY, EVENT_ANALYSIS
    result = Column(JSON, nullable=False, default=dict)
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False, index=True)

    # Relationships
    merchant = relationship("Merchant")
    business_event = relationship("BusinessEvent")

    def __repr__(self):
        return f"<IntelligenceResult(id='{self.id}', type='{self.result_type}', merchant='{self.merchant_id}')>"
