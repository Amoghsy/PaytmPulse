from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum


class FinancialNeedType(str, Enum):
    WORKING_CAPITAL = "WORKING_CAPITAL"
    INVENTORY_FINANCING = "INVENTORY_FINANCING"
    BUSINESS_EXPANSION = "BUSINESS_EXPANSION"
    CASH_FLOW_SUPPORT = "CASH_FLOW_SUPPORT"


class FinancialRecommendationStatus(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    INTERESTED = "INTERESTED"
    DECLINED = "DECLINED"
    NOT_INTERESTED = "NOT_INTERESTED"
    EXPIRED = "EXPIRED"


class FinancialProductResponse(BaseModel):
    id: str
    product_code: str
    name: str
    category: str
    description: str
    min_signal_confidence: float
    max_simulated_amount: float
    duration_days: int
    interest_rate_display: str
    simulated: bool = True
    active: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinancialNeedDetectionResult(BaseModel):
    merchant_id: str
    need_detected: bool = False
    need_type: Optional[FinancialNeedType] = None
    reason: str = ""
    supporting_signals: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    estimated_requirement_amount: float = 0.0
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class FinancialRecommendationResponse(BaseModel):
    id: str
    merchant_id: str
    product_id: str
    need_type: str
    title: str
    reason: str
    supporting_signals: List[str]
    confidence: float
    simulated_amount: float
    duration_days: int
    status: str
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    interest_rate_display: Optional[str] = "Competitive Partner Rate"
    disclaimer: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FinancialOpportunityResponse(BaseModel):
    merchant_id: str
    opportunity_detected: bool
    need_result: Optional[FinancialNeedDetectionResult] = None
    matched_product: Optional[FinancialProductResponse] = None
    recommendation: Optional[FinancialRecommendationResponse] = None
    message: str = ""


class MerchantInterestRequest(BaseModel):
    notes: Optional[str] = None


class MerchantDeclineRequest(BaseModel):
    reason: Optional[str] = None
