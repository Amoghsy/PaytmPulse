from sqlalchemy import Column, String, Numeric, Integer, Boolean, Text, DateTime, func
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, utc_now


class FinancialProduct(Base):
    __tablename__ = "financial_products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False)
    min_signal_confidence = Column(Numeric(3, 2), nullable=False, default=0.70)
    max_simulated_amount = Column(Numeric(12, 2), nullable=False, default=50000.00)
    duration_days = Column(Integer, nullable=False, default=90)
    interest_rate_display = Column(String(50), nullable=False, default="Simulated Demo Rate")
    simulated = Column(Boolean, nullable=False, default=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    recommendations = relationship("FinancialRecommendation", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FinancialProduct(id='{self.id}', product_code='{self.product_code}', category='{self.category}')>"
