from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    name: str
    category: str
    price: float
    cost_price: float
    current_stock: int = 0
    reorder_level: int = 10
    supplier: Optional[str] = None
    average_daily_sales: float = 0.0
    is_active: bool = True


class ProductCreate(ProductBase):
    merchant_id: str


class ProductOut(ProductBase):
    id: str
    merchant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
