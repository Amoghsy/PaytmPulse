from sqlalchemy import Column, String, Numeric, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, utc_now


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    total_spend = Column(Numeric(12, 2), nullable=False, default=0.00)
    purchase_count = Column(Integer, nullable=False, default=0)
    last_purchase_at = Column(DateTime(timezone=True), nullable=True)
    average_purchase_interval = Column(Numeric(8, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    merchant = relationship("Merchant", back_populates="customers")
    transactions = relationship("Transaction", back_populates="customer")

    def __repr__(self):
        return f"<Customer(id='{self.id}', name='{self.name}', total_spend={self.total_spend})>"
