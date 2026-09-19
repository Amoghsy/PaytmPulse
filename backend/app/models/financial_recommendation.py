from sqlalchemy import Column, String, Numeric, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, generate_uuid, utc_now


class FinancialRecommendationStatus(str, enum.Enum):
    RECOMMENDED = "RECOMMENDED"
    INTERESTED = "INTERESTED"
    DECLINED = "DECLINED"
    NOT_INTERESTED = "NOT_INTERESTED"
    EXPIRED = "EXPIRED"


class FinancialRecommendation(Base):
    __tablename__ = "financial_recommendations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("financial_products.id", ondelete="CASCADE"), nullable=False, index=True)
    need_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    supporting_signals = Column(JSON, nullable=False, default=list)
    confidence = Column(Numeric(3, 2), nullable=False, default=0.80)
    simulated_amount = Column(Numeric(12, 2), nullable=False, default=25000.00)
    duration_days = Column(Numeric(5, 0), nullable=False, default=90)
    status = Column(SQLEnum(FinancialRecommendationStatus, native_enum=False), nullable=False, default=FinancialRecommendationStatus.RECOMMENDED, index=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    merchant = relationship("Merchant", backref="financial_recommendations")
    product = relationship("FinancialProduct", back_populates="recommendations")

    def __repr__(self):
        return f"<FinancialRecommendation(id='{self.id}', merchant_id='{self.merchant_id}', need_type='{self.need_type}', status='{self.status}')>"
