"""
Paytm Pulse - Phase 6 Decision Engine Schemas
Pydantic data models for candidate action generation, scoring, prioritization, and approval endpoints.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class EstimatedImpact(BaseModel):
    """Estimated business and revenue outcome of taking this action."""
    type: str = Field(
        ...,
        description="Type of impact, e.g. REVENUE_PROTECTED, INCREMENTAL_REVENUE, RECOVERED_REVENUE, COST_SAVINGS"
    )
    value: float = Field(..., ge=0.0, description="Estimated monetary value in INR")
    currency: str = Field(default="INR", description="Currency symbol or code")
    details: Optional[str] = Field(default=None, description="Human readable explanation of how impact was calculated")


class NextBestAction(BaseModel):
    """
    Structured, merchant-approvable Next Best Action produced by the Decision Engine.
    """
    id: Optional[str] = Field(None, description="Unique Action / Recommendation ID")
    merchant_id: str = Field(..., description="Unique merchant ID")
    event_id: Optional[str] = Field(None, description="Associated business event ID if applicable")
    recommendation_id: Optional[str] = Field(None, description="Associated Recommendation record ID in DB")
    action_type: str = Field(
        ...,
        description="Action type: RESTOCK_PRODUCT, RUN_PROMOTION, CREATE_BUNDLE, CUSTOMER_WINBACK, CROSS_SELL, MONITOR_TREND, FINANCIAL_PRODUCT_RECOMMENDATION"
    )
    title: str = Field(..., description="Concise action headline for the merchant")
    description: str = Field(..., description="Action instructions or summary")
    reason: str = Field(..., description="Evidence-grounded rationale explaining why this action is recommended")
    priority: str = Field(..., description="Priority tier: CRITICAL, HIGH, MEDIUM, LOW")
    urgency: str = Field(..., description="Urgency level: CRITICAL, HIGH, MEDIUM, LOW")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Engine confidence score")
    estimated_impact: EstimatedImpact = Field(..., description="Estimated business/revenue impact")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Machine-readable parameters for downstream execution (product_id, quantity, discount_percentage, etc.)"
    )
    requires_approval: bool = Field(default=True, description="Always true in Phase 6; requires merchant confirmation")
    status: str = Field(
        default="PENDING_APPROVAL",
        description="Current state: PENDING_APPROVAL, APPROVED, REJECTED, EXECUTED"
    )
    score: float = Field(default=0.0, description="Internal composite ranking score")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of decision creation")


class GenerateDecisionRequest(BaseModel):
    """Payload to trigger Next Best Action decision generation."""
    merchant_id: str = Field(..., description="Unique ID of the merchant")
    event_id: Optional[str] = Field(None, description="Optional BusinessEvent ID to trigger targeted event decision")


class DecisionResponse(BaseModel):
    """Response containing selected Next Best Action and alternative ranked candidates."""
    merchant_id: str = Field(..., description="Merchant ID")
    event_id: Optional[str] = Field(None, description="Event ID if triggered by business event")
    next_best_action: Optional[NextBestAction] = Field(None, description="Highest priority Next Best Action")
    alternative_actions: List[NextBestAction] = Field(
        default_factory=list,
        description="Alternative candidate actions ranked by score"
    )
    total_candidates: int = Field(default=0, description="Total candidate actions evaluated")
    created_at: str = Field(..., description="ISO timestamp")


class DecisionActionResponse(BaseModel):
    """Response payload for approval/rejection state transitions."""
    decision_id: str = Field(..., description="Recommendation / Action ID")
    status: str = Field(..., description="Updated status: APPROVED or REJECTED")
    message: str = Field(..., description="State transition confirmation message")
