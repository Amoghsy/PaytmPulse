"""
Paytm Pulse - Phase 5 Agent Schemas
Pydantic data models for structured business reasoning outputs and agent endpoints.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ImpactEstimate(BaseModel):
    """Estimated business and financial impact."""
    type: str = Field(
        ...,
        description="Type of impact, e.g. POTENTIAL_REVENUE_LOSS, REVENUE_GROWTH, CUSTOMER_RETENTION, INVENTORY_HOLDING_COST"
    )
    estimated_value: float = Field(
        ...,
        description="Estimated value in INR"
    )
    currency: str = Field(default="INR", description="Currency symbol/code")


class AgentAnalysis(BaseModel):
    """
    Structured reasoning output produced by the Paytm Pulse AI Business Intelligence Agent.
    Strictly populated with evidence and numerical values derived from Phase 4 tools.
    """
    event_id: Optional[str] = Field(None, description="Associated business event ID if applicable")
    merchant_id: str = Field(..., description="Unique merchant ID")
    summary: str = Field(..., description="Concise executive summary of what is happening")
    detected_issue: str = Field(..., description="Underlying business issue, opportunity or pattern detected")
    evidence: List[str] = Field(
        default_factory=list,
        description="Empirical observations and ML facts supporting the diagnosis"
    )
    impact: ImpactEstimate = Field(
        ...,
        description="Estimated financial or business impact"
    )
    urgency: str = Field(
        ...,
        description="Urgency level: LOW, MEDIUM, HIGH, CRITICAL"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0 based on data volume and model confidence"
    )
    recommendation: str = Field(
        ...,
        description="Actionable, non-executing recommendation tailored for the merchant"
    )
    supporting_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data payloads collected from Phase 4 intelligence tools"
    )
    suggested_action_type: str = Field(
        ...,
        description="Action type for downstream Phase 6 Next Best Action engine (e.g. RESTOCK, PROMOTION, WINBACK, CROSS_SELL, MONITOR)"
    )


class AnalyzeEventRequest(BaseModel):
    """Request payload to analyze a specific business event."""
    event_id: str = Field(..., description="Unique ID of the BusinessEvent to analyze")


class AnalyzeMerchantRequest(BaseModel):
    """Request payload to perform general business health analysis for a merchant."""
    merchant_id: str = Field(..., description="Unique ID of the Merchant")


class ChatRequest(BaseModel):
    """Request payload for merchant conversational queries."""
    merchant_id: str = Field(..., description="Unique ID of the Merchant")
    message: str = Field(..., min_length=1, description="Merchant natural language question or prompt")
    language: Optional[str] = Field(default=None, description="Target language code or name for AI response (e.g. 'en', 'kn', 'hi', 'mr')")


class ChatResponse(BaseModel):
    """Response payload for merchant conversational queries."""
    merchant_id: str = Field(..., description="Unique ID of the Merchant")
    response: str = Field(..., description="Merchant-friendly natural language answer grounded in business data")
    supporting_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Numerical facts, top products, or forecast charts supporting the answer"
    )
    suggested_action: Optional[str] = Field(
        default=None,
        description="Suggested action tag or null"
    )
