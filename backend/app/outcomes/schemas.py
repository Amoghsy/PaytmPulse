from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from enum import Enum


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OutcomeType(str, Enum):
    REVENUE_INCREASE = "REVENUE_INCREASE"
    REVENUE_PROTECTED = "REVENUE_PROTECTED"
    STOCKOUT_PREVENTED = "STOCKOUT_PREVENTED"
    POTENTIAL_STOCKOUT_PREVENTED = "POTENTIAL_STOCKOUT_PREVENTED"
    STOCKOUT_OCCURRED = "STOCKOUT_OCCURRED"
    CUSTOMERS_RECOVERED = "CUSTOMERS_RECOVERED"
    CUSTOMER_RETENTION = "CUSTOMER_RETENTION"
    PROMOTION_CONVERSION = "PROMOTION_CONVERSION"
    DEMAND_SATISFIED = "DEMAND_SATISFIED"
    NO_MEASURABLE_IMPACT = "NO_MEASURABLE_IMPACT"
    NEGATIVE_IMPACT = "NEGATIVE_IMPACT"
    TREND_CONFIRMED = "TREND_CONFIRMED"
    TREND_RESOLVED = "TREND_RESOLVED"
    TREND_ESCALATED = "TREND_ESCALATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class OutcomeStatus(str, Enum):
    PENDING = "PENDING"
    MEASURING = "MEASURING"
    MEASURED = "MEASURED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    FAILED = "FAILED"


class OutcomeImpact(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class OutcomeConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class BaselineSnapshot(BaseModel):
    captured_at: datetime = Field(default_factory=utc_now)
    product_id: Optional[str] = None
    sales_before: float = 0.0
    revenue_before: float = 0.0
    transactions_before: int = 0
    inventory_before: Optional[int] = None
    customer_activity_before: Optional[int] = None
    product_demand_before: Optional[float] = None
    stock_level_before: Optional[int] = None
    historical_sales_velocity: Optional[float] = None
    historical_daily_revenue: Optional[float] = None
    historical_avg_order_value: Optional[float] = None
    target_customer_count: Optional[int] = None
    target_customer_ids: Optional[List[str]] = None
    historical_conversion_rate: Optional[float] = None
    expected_sales_window: Optional[float] = None
    baseline_start_time: Optional[datetime] = None
    baseline_end_time: Optional[datetime] = None
    measurement_start_time: Optional[datetime] = None
    measurement_end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ObservedMetrics(BaseModel):
    collected_at: datetime = Field(default_factory=utc_now)
    window_hours_observed: float = 0.0
    transactions_count: int = 0
    units_sold: int = 0
    actual_sales_revenue: float = 0.0
    sales_after: float = 0.0
    revenue_after: float = 0.0
    inventory_after: Optional[int] = None
    final_stock_level: Optional[int] = None
    stockout_occurred: bool = False
    returning_customers_count: int = 0
    returning_customer_ids: List[str] = Field(default_factory=list)
    offer_conversions: int = 0
    secondary_units_sold: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ImpactCalculationResult(BaseModel):
    outcome_type: OutcomeType = OutcomeType.NO_MEASURABLE_IMPACT
    impact: OutcomeImpact = OutcomeImpact.NEUTRAL
    confidence: OutcomeConfidence = OutcomeConfidence.MEDIUM
    confidence_score: float = 0.8
    sales_before: float = 0.0
    sales_after: float = 0.0
    expected_sales: float = 0.0
    revenue_change: float = 0.0
    revenue_change_percent: float = 0.0
    baseline_adjusted_revenue_change: float = 0.0
    stockout_prevented: bool = False
    customers_recovered: int = 0
    offer_conversion: Optional[float] = None
    reasoning: str = ""


class LearningSignal(BaseModel):
    action_type: str
    recommended: bool = True
    approved: bool = True
    executed: bool = True
    outcome_type: str = "NO_MEASURABLE_IMPACT"
    impact: str = "NEUTRAL"
    confidence: float = 0.8
    signal: str = ""
    adaptation_rule: str = ""
    timestamp: datetime = Field(default_factory=utc_now)


class OutcomeResponse(BaseModel):
    id: str
    action_id: str
    outcome_type: Optional[str] = None
    status: str
    confidence: Optional[str] = None
    sales_before: Optional[float] = None
    sales_after: Optional[float] = None
    revenue_change: Optional[float] = None
    stockout_prevented: bool = False
    customers_recovered: int = 0
    offer_conversion: Optional[float] = None
    impact: Optional[str] = None
    baseline_metrics: Optional[Dict[str, Any]] = None
    observed_metrics: Optional[Dict[str, Any]] = None
    learning_signals: Optional[Dict[str, Any]] = None
    measured_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutcomeTraceResponse(BaseModel):
    outcome_id: str
    action_id: str
    execution_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    event_id: Optional[str] = None
    merchant_id: str
    action_type: str
    status: str
    impact: Optional[str] = None
    revenue_change: Optional[float] = None
    stockout_prevented: bool = False
    customers_recovered: int = 0
    learning_summary: Optional[str] = None
    action_details: Dict[str, Any] = Field(default_factory=dict)
    recommendation_details: Optional[Dict[str, Any]] = None
    event_details: Optional[Dict[str, Any]] = None


class MerchantOutcomeSummary(BaseModel):
    merchant_id: str
    period: str = "last_30_days"
    actions_executed: int = 0
    total_actions_measured: int = 0
    outcomes_measured: int = 0
    positive_outcomes: int = 0
    neutral_outcomes: int = 0
    negative_outcomes: int = 0
    insufficient_data: int = 0
    insufficient_data_outcomes: int = 0
    stockouts_prevented: int = 0
    customers_recovered: int = 0
    revenue_change: float = 0.0
    observed_revenue_change: float = 0.0
    avg_conversion_rate: Optional[float] = None
