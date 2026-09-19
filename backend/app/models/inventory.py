from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, utc_now


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint("current_stock >= 0", name="chk_inventory_stock_non_negative"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    current_stock = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=10)
    maximum_stock = Column(Integer, nullable=False, default=100)
    last_restocked_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    product = relationship("Product", back_populates="inventory")

    def __repr__(self):
        return f"<Inventory(product_id='{self.product_id}', current_stock={self.current_stock}, reorder_level={self.reorder_level})>"
