from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class InventoryBase(BaseModel):
    current_stock: int
    reorder_level: int
    maximum_stock: int
    last_restocked_at: Optional[datetime] = None


class InventoryOut(InventoryBase):
    id: str
    product_id: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MerchantInventoryItem(BaseModel):
    product_id: str
    product_name: str
    category: str
    current_stock: int
    reorder_level: int
    maximum_stock: int
    price: float
    average_daily_sales: float
    last_restocked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
