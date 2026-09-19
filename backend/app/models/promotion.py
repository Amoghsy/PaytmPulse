import enum
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, utc_now


class PromotionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SCHEDULED = "SCHEDULED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    action_id = Column(String(36), ForeignKey("actions.id", ondelete="SET NULL"), nullable=True, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    discount_percentage = Column(Float, nullable=False, default=10.0)
    target_segment = Column(String(100), nullable=True, default="ALL")
    start_time = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(PromotionStatus, native_enum=False), nullable=False, default=PromotionStatus.ACTIVE, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    merchant = relationship("Merchant")
    action = relationship("Action")
    product = relationship("Product")

    def __repr__(self):
        return f"<Promotion(id='{self.id}', product_id='{self.product_id}', discount={self.discount_percentage}%, status='{self.status}')>"
