from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.transaction import PaymentMethod


class TransactionBase(BaseModel):
    quantity: int
    unit_price: float
    amount: float
    payment_method: PaymentMethod
    transaction_timestamp: datetime


class TransactionCreate(TransactionBase):
    merchant_id: str
    product_id: str
    customer_id: Optional[str] = None


class TransactionOut(TransactionBase):
    id: str
    merchant_id: str
    product_id: str
    customer_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
