from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, utc_now


class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    cost_price = Column(Numeric(10, 2), nullable=False)
    current_stock = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=10)
    supplier = Column(String(255), nullable=True)
    average_daily_sales = Column(Numeric(10, 2), nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    merchant = relationship("Merchant", back_populates="products")
    inventory = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="product")

    def __repr__(self):
        return f"<Product(id='{self.id}', name='{self.name}', price={self.price}, stock={self.current_stock})>"
