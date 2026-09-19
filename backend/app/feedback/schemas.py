from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict, computed_field
from datetime import datetime, timezone
from app.feedback.config import FeedbackType, RecommendationEffectiveness


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FeedbackSignalCreate(BaseModel):
    merchant_id: str
    event_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    action_id: Optional[str] = None
    execution_id: Optional[str] = None
    outcome_id: Optional[str] = None
    action_type: Optional[str] = None
    recommendation_confidence: Optional[float] = None
    merchant_decision: Optional[str] = None
    execution_status: Optional[str] = None
    outcome_type: Optional[str] = None
    outcome_classification: Optional[str] = None
    outcome_impact: Optional[str] = None
    objective_impact: Optional[str] = None
    outcome_confidence: Optional[str] = None
    revenue_change: Optional[float] = None
    stockout_prevented: Optional[bool] = None
    customers_recovered: Optional[int] = None
    offer_conversion_rate: Optional[float] = None
    feedback_type: str
    merchant_rating: Optional[str] = None
    merchant_feedback_text: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    metadata_payload: Optional[Dict[str, Any]] = None


class MerchantRatingPayload(BaseModel):
    merchant_id: str
    recommendation_id: Optional[str] = None
    action_id: Optional[str] = None
    rating: Optional[str] = None
    rating_useful: Optional[bool] = None
    stars: Optional[int] = None
    feedback_text: Optional[str] = None
    feedback_comment: Optional[str] = None


class FeedbackSignalResponse(BaseModel):
    id: str
    merchant_id: str
    event_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    action_id: Optional[str] = None
    execution_id: Optional[str] = None
    outcome_id: Optional[str] = None
    action_type: Optional[str] = None
    recommendation_confidence: Optional[float] = None
    merchant_decision: Optional[str] = None
    execution_status: Optional[str] = None
    outcome_type: Optional[str] = None
    outcome_classification: Optional[str] = None
    outcome_impact: Optional[str] = None
    outcome_confidence: Optional[str] = None
    feedback_type: str
    merchant_rating: Optional[str] = None
    merchant_feedback_text: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def objective_impact(self) -> Optional[str]:
        return self.outcome_impact

    @computed_field
    @property
    def is_useful(self) -> Optional[bool]:
        if self.merchant_rating:
            return self.merchant_rating.upper() == "USEFUL"
        return None

    @computed_field
    @property
    def user_rating(self) -> Optional[int]:
        if self.metadata_json and "stars" in self.metadata_json:
            return self.metadata_json["stars"]
        return 5 if self.merchant_rating == "USEFUL" else None

    @computed_field
    @property
    def feedback_notes(self) -> Optional[str]:
        return self.merchant_feedback_text


class RecommendationEffectivenessResponse(BaseModel):
    recommendation_id: str
    action_id: Optional[str] = None
    merchant_id: str
    action_type: Optional[str] = None
    title: Optional[str] = None
    merchant_decision: str = "UNKNOWN"
    execution_status: Optional[str] = None
    outcome_classification: Optional[str] = None
    merchant_rating: Optional[str] = None
    effectiveness: str
    explanation: str
    timeline: Dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def was_approved(self) -> bool:
        return self.merchant_decision == "APPROVED"

    @computed_field
    @property
    def was_executed(self) -> bool:
        return self.execution_status == "EXECUTED"

    @computed_field
    @property
    def is_terminal(self) -> bool:
        return self.effectiveness in ["SUCCESSFUL", "PARTIALLY_SUCCESSFUL", "UNSUCCESSFUL", "EXECUTION_FAILED", "REJECTED", "EXPIRED"]

    @computed_field
    @property
    def net_revenue_change(self) -> Optional[float]:
        return self.timeline.get("revenue_change")

    @computed_field
    @property
    def stockout_prevented(self) -> Optional[bool]:
        return self.timeline.get("stockout_prevented")

    @computed_field
    @property
    def merchant_notes(self) -> Optional[str]:
        return self.timeline.get("merchant_notes")


class ActionTypePerformanceSummary(BaseModel):
    action_type: str
    recommendations_generated: int = 0
    recommendations_approved: int = 0
    recommendations_rejected: int = 0
    recommendations_expired: int = 0
    actions_executed: int = 0
    actions_failed: int = 0
    positive_outcomes: int = 0
    neutral_outcomes: int = 0
    negative_outcomes: int = 0
    insufficient_data: int = 0
    approval_rate: float = 0.0
    success_rate: float = 0.0
    average_outcome_confidence: Optional[float] = None
    performance_score_adjustment: float = 0.0


class MerchantFeedbackSummary(BaseModel):
    merchant_id: str
    total_recommendations: int = 0
    recommendations_generated: int = 0
    total_approved: int = 0
    approved: int = 0
    total_rejected: int = 0
    rejected: int = 0
    total_expired: int = 0
    expired: int = 0
    total_executed: int = 0
    executed: int = 0
    total_execution_failed: int = 0
    execution_failed: int = 0
    total_measured: int = 0
    successful_actions: int = 0
    positive_outcomes: int = 0
    neutral_outcomes: int = 0
    negative_outcomes: int = 0
    insufficient_data: int = 0
    merchant_useful_ratings: int = 0
    merchant_not_useful_ratings: int = 0
    approval_rate: float = 0.0
    success_rate: float = 0.0
    outcome_success_rate: float = 0.0
    net_revenue_change: float = 0.0


class LearningDatasetRow(BaseModel):
    merchant_id: str
    event_type: Optional[str] = None
    action_type: Optional[str] = None
    recommendation_confidence: Optional[float] = None
    urgency: Optional[str] = None
    estimated_impact: Optional[str] = None
    merchant_decision: Optional[str] = None
    execution_status: Optional[str] = None
    outcome_type: Optional[str] = None
    outcome_classification: Optional[str] = None
    observed_impact: Optional[str] = None
    outcome_confidence: Optional[str] = None
    merchant_feedback: Optional[str] = None
    effectiveness: Optional[str] = None
    created_at: datetime
