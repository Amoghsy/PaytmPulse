from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base, generate_uuid, utc_now


class MerchantCategory(str, enum.Enum):
    KIRANA = "KIRANA"
    RESTAURANT = "RESTAURANT"
    PHARMACY = "PHARMACY"
    CLOTHING = "CLOTHING"
    ELECTRONICS = "ELECTRONICS"
    OTHER = "OTHER"


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    shop_name = Column(String(255), nullable=False)
    category = Column(SQLEnum(MerchantCategory, native_enum=False), nullable=False)
    location = Column(String(255), nullable=False)
    language = Column(String(50), nullable=False, default="Hindi")
    phone = Column(String(20), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    products = relationship("Product", back_populates="merchant", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="merchant", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="merchant", cascade="all, delete-orphan")
    business_events = relationship("BusinessEvent", back_populates="merchant", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="merchant", cascade="all, delete-orphan")
    actions = relationship("Action", back_populates="merchant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Merchant(id='{self.id}', shop_name='{self.shop_name}', category='{self.category}')>"
