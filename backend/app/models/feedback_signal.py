from sqlalchemy import Column, String, Numeric, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, utc_now


class FeedbackSignal(Base):
    __tablename__ = "feedback_signals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(36), nullable=True, index=True)
    recommendation_id = Column(String(36), ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=True, index=True)
    action_id = Column(String(36), ForeignKey("actions.id", ondelete="CASCADE"), nullable=True, index=True)
    execution_id = Column(String(50), nullable=True)
    outcome_id = Column(String(36), ForeignKey("outcomes.id", ondelete="CASCADE"), nullable=True, index=True)

    action_type = Column(String(50), nullable=True, index=True)
    recommendation_confidence = Column(Numeric(4, 2), nullable=True)

    merchant_decision = Column(String(30), nullable=True)  # APPROVED, REJECTED, EXPIRED, IGNORED
    execution_status = Column(String(30), nullable=True)   # EXECUTED, FAILED, PENDING

    outcome_type = Column(String(50), nullable=True)
    outcome_classification = Column(String(30), nullable=True)
    outcome_impact = Column(String(30), nullable=True)     # POSITIVE, NEUTRAL, NEGATIVE, INSUFFICIENT_DATA
    outcome_confidence = Column(String(20), nullable=True)

    feedback_type = Column(String(50), nullable=False, index=True)
    merchant_rating = Column(String(20), nullable=True)    # USEFUL, NOT_USEFUL, NEUTRAL
    merchant_feedback_text = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False, index=True)

    # Relationships
    merchant = relationship("Merchant")
    recommendation = relationship("Recommendation")
    action = relationship("Action")
    outcome = relationship("Outcome")

    def __repr__(self):
        return f"<FeedbackSignal(id='{self.id}', merchant_id='{self.merchant_id}', type='{self.feedback_type}', rating='{self.merchant_rating}')>"
