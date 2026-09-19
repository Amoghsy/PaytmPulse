from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime
from app.models.business_event import EventType, EventSeverity


class BusinessEventBase(BaseModel):
    merchant_id: str
    event_type: EventType
    severity: EventSeverity = EventSeverity.MEDIUM
    source: str = "rule_engine"
    payload: Dict[str, Any] = {}
    processed: bool = False


class BusinessEventCreate(BusinessEventBase):
    detected_at: Optional[datetime] = None


class BusinessEventResponse(BusinessEventBase):
    id: str
    detected_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
