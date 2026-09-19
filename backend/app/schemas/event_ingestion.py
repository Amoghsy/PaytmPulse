from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Union
from datetime import datetime
from app.models.transaction import PaymentMethod


class TransactionEventPayload(BaseModel):
    external_event_id: Optional[str] = Field(
        default=None,
        description="Optional unique external event ID for idempotency deduplication",
        example="evt_tx_9876543210"
    )
    merchant_id: str = Field(..., description="UUID of the merchant", example="merchant-uuid-here")
    product_id: str = Field(..., description="UUID of the product", example="product-uuid-here")
    customer_id: Optional[str] = Field(default=None, description="UUID of the customer", example="customer-uuid-here")
    quantity: int = Field(default=1, gt=0, description="Quantity of items purchased", example=2)
    unit_price: float = Field(default=100.0, gt=0, description="Unit price per item in INR", example=150.00)
    payment_method: Union[PaymentMethod, str] = Field(default=PaymentMethod.UPI, description="Payment method used")
    transaction_timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the transaction (ISO 8601 string or datetime). Defaults to now UTC if omitted."
    )

    @field_validator("payment_method", mode="before")
    @classmethod
    def normalize_payment_method(cls, v):
        if not v:
            return PaymentMethod.UPI
        if isinstance(v, PaymentMethod):
            return v
        v_str = str(v).strip().upper()
        if v_str in ("UPI", "CARD", "CASH", "OTHER"):
            return PaymentMethod(v_str)
        return PaymentMethod.UPI

    @field_validator("quantity", mode="before")
    @classmethod
    def parse_quantity(cls, v):
        try:
            val = int(v)
            return val if val > 0 else 1
        except Exception:
            return 1

    @field_validator("unit_price", mode="before")
    @classmethod
    def parse_unit_price(cls, v):
        try:
            val = float(v)
            return val if val > 0 else 100.0
        except Exception:
            return 100.0


class IngestionResponse(BaseModel):
    status: str = Field(..., example="success")
    message: str = Field(..., example="Transaction ingested and processed successfully")
    transaction_id: str = Field(..., example="tx-uuid-12345")
    external_event_id: Optional[str] = Field(default=None, example="evt_tx_9876543210")
    detected_events: list = Field(default_factory=list, description="List of business events detected triggered by this transaction")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of updated merchant state")

