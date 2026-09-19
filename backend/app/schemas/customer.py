from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CustomerBase(BaseModel):
    name: str
    phone: str
    total_spend: float = 0.00
    purchase_count: int = 0
    last_purchase_at: Optional[datetime] = None
    average_purchase_interval: Optional[float] = None


class CustomerCreate(CustomerBase):
    merchant_id: str


class CustomerOut(CustomerBase):
    id: str
    merchant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
