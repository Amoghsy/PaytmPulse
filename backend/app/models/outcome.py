from sqlalchemy import Column, String, Numeric, Integer, Boolean, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, utc_now


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    action_id = Column(String(36), ForeignKey("actions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    outcome_type = Column(String(50), nullable=True)
    status = Column(String(30), nullable=False, default="MEASURED")
    confidence = Column(String(20), nullable=True, default="MEDIUM")
    sales_before = Column(Numeric(12, 2), nullable=True)
    sales_after = Column(Numeric(12, 2), nullable=True)
    revenue_change = Column(Numeric(12, 2), nullable=True)
    stockout_prevented = Column(Boolean, nullable=False, default=False)
    customers_recovered = Column(Integer, nullable=False, default=0)
    offer_conversion = Column(Numeric(5, 2), nullable=True)
    impact = Column(Text, nullable=True)
    baseline_metrics = Column(JSON, nullable=True)
    observed_metrics = Column(JSON, nullable=True)
    learning_signals = Column(JSON, nullable=True)
    measured_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    action = relationship("Action", back_populates="outcome")

    def __repr__(self):
        return f"<Outcome(id='{self.id}', action_id='{self.action_id}', impact='{self.impact}', revenue_change={self.revenue_change})>"

