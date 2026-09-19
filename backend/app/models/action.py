from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, generate_uuid, utc_now


class ActionType(str, enum.Enum):
    REORDER = "REORDER"
    SEND_OFFER = "SEND_OFFER"
    WINBACK = "WINBACK"
    PROMOTION = "PROMOTION"
    FINANCIAL_PRODUCT = "FINANCIAL_PRODUCT"


class ActionStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Action(Base):
    __tablename__ = "actions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    recommendation_id = Column(String(36), ForeignKey("recommendations.id", ondelete="SET NULL"), nullable=True, index=True)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(SQLEnum(ActionType, native_enum=False), nullable=False)
    parameters = Column(JSON, nullable=False, default=dict)
    status = Column(SQLEnum(ActionStatus, native_enum=False), nullable=False, default=ActionStatus.PENDING, index=True)
    execution_id = Column(String(100), nullable=True, index=True)
    execution_result = Column(JSON, nullable=True)
    failure_reason = Column(String(500), nullable=True)
    retry_count = Column(String(10), nullable=False, default="0")
    approved_at = Column(DateTime(timezone=True), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    merchant = relationship("Merchant", back_populates="actions")
    recommendation = relationship("Recommendation", back_populates="actions")
    outcome = relationship("Outcome", back_populates="action", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Action(id='{self.id}', action_type='{self.action_type}', status='{self.status}')>"
