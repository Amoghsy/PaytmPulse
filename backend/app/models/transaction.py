from sqlalchemy import Column, String, Numeric, Integer, DateTime, ForeignKey, Index, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, generate_uuid, utc_now


class PaymentMethod(str, enum.Enum):
    UPI = "UPI"
    CARD = "CARD"
    CASH = "CASH"
    OTHER = "OTHER"


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("idx_transactions_merchant_timestamp", "merchant_id", "transaction_timestamp"),
        Index("idx_transactions_merchant_product_timestamp", "merchant_id", "product_id", "transaction_timestamp"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(SQLEnum(PaymentMethod, native_enum=False), nullable=False, default=PaymentMethod.UPI)
    external_event_id = Column(String(100), unique=True, nullable=True, index=True)
    transaction_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    merchant = relationship("Merchant", back_populates="transactions")
    product = relationship("Product", back_populates="transactions")
    customer = relationship("Customer", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id='{self.id}', amount={self.amount}, timestamp='{self.transaction_timestamp}')>"
