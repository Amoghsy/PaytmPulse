from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class AnomalyDetectionRequest(BaseModel):
    merchant_id: str = Field(..., description="Merchant UUID")
    product_id: Optional[str] = Field(default=None, description="Optional Product UUID to analyze single product")
    days: int = Field(default=30, ge=1, le=90)


class DemandForecastRequest(BaseModel):
    merchant_id: str = Field(..., description="Merchant UUID")
    product_id: str = Field(..., description="Product UUID to forecast")
    days: int = Field(default=30, ge=1, le=90)


class StockoutPredictionRequest(BaseModel):
    merchant_id: str = Field(..., description="Merchant UUID")
    product_id: Optional[str] = Field(default=None, description="Optional Product UUID. If omitted, predicts across all products.")


class EventAnalysisRequest(BaseModel):
    event_id: str = Field(..., description="Phase 3 BusinessEvent UUID")


class ModelTrainingRequest(BaseModel):
    merchant_id: str = Field(..., description="Merchant UUID")
    product_id: Optional[str] = Field(default=None, description="Optional Product UUID for demand model")
    model_type: str = Field(default="all", description="all, anomaly, or demand")
    days: int = Field(default=30, ge=1, le=90)
