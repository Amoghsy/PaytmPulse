from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.merchant import MerchantCategory


class MerchantBase(BaseModel):
    name: str
    shop_name: str
    category: MerchantCategory
    location: str
    language: str = "Hindi"
    phone: str


class MerchantCreate(MerchantBase):
    pass


class MerchantOut(MerchantBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MerchantSummary(BaseModel):
    merchant_id: str
    shop_name: str
    category: str
    location: str
    total_products: int
    total_customers: int
    total_transactions: int
    total_revenue: float
