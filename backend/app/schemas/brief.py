from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class KeyMetricItem(BaseModel):
    label: str
    value: str
    trend: str = "FLAT"  # UP, DOWN, FLAT
    change: Optional[str] = None


class InsightItem(BaseModel):
    type: str = "SALES"
    title: str
    description: str
    severity: str = "INFO"  # INFO, WARNING, OPPORTUNITY


class AttentionItem(BaseModel):
    type: str = "STOCKOUT_RISK"
    title: str
    description: str
    urgency: str = "HIGH"  # HIGH, MEDIUM, LOW


class OpportunityItem(BaseModel):
    type: str = "PROMOTION"
    title: str
    description: str
    expected_impact: Optional[str] = None
    confidence: Optional[str] = None


class RecommendedActionItem(BaseModel):
    action_type: str = "MONITOR"
    title: str
    reason: str
    requires_approval: bool = True


class StructuredBriefContent(BaseModel):
    headline: str
    summary: str
    key_metrics: List[KeyMetricItem] = []
    important_insights: List[InsightItem] = []
    attention_items: List[AttentionItem] = []
    opportunities: List[OpportunityItem] = []
    recommended_actions: List[RecommendedActionItem] = []
    closing_message: Optional[str] = None


class MerchantBriefContext(BaseModel):
    merchant: Dict[str, Any]
    sales: Dict[str, Any] = {}
    inventory_risks: List[Dict[str, Any]] = []
    customer_intelligence: Dict[str, Any] = {}
    opportunities: List[Dict[str, Any]] = []
    recent_events: List[Dict[str, Any]] = []
    collected_at: str


class GenerateBriefRequest(BaseModel):
    merchant_id: str
    language: Optional[str] = None
    brief_date: Optional[str] = None
    force_refresh: Optional[bool] = False


class StoreBriefRequest(BaseModel):
    merchant_id: str
    brief_date: Optional[str] = None
    brief: Dict[str, Any]
    generated_by: Optional[str] = "gemini"
    language: Optional[str] = "en"


class SendWhatsAppBriefRequest(BaseModel):
    custom_message: Optional[str] = None


class BusinessBriefOut(BaseModel):
    id: str
    merchant_id: str
    brief_date: str
    headline: str
    summary: str
    content: Dict[str, Any]
    generated_by: str
    language: str
    dashboard_delivered: bool = True
    whatsapp_delivered: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
