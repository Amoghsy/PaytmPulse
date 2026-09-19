"""
Paytm Pulse - Phase 5 Agent Tools Registry
Exports controlled, read-only intelligence tools for Google ADK / Gemini agent.
"""

from app.agent.tools.sales_tools import get_sales_analysis
from app.agent.tools.anomaly_tools import detect_anomalies
from app.agent.tools.forecast_tools import forecast_demand
from app.agent.tools.inventory_tools import predict_stockout, get_all_stockout_risks
from app.agent.tools.customer_tools import get_customer_intelligence
from app.agent.tools.opportunity_tools import detect_opportunities
from app.agent.tools.event_tools import get_business_event
from app.agent.tools.decision_tools import generate_next_best_actions
from app.agent.tools.outcome_tools import get_action_outcome, get_action_history
from app.agent.tools.financial_tools import get_financial_opportunities
from app.agent.tools.memory_tools import get_recent_merchant_context
from app.agent.tools.feedback_tools import get_recommendation_feedback, get_merchant_feedback_summary
from app.agent.tools.simulation_tools import simulate_business_action

__all__ = [
    "get_sales_analysis",
    "detect_anomalies",
    "forecast_demand",
    "predict_stockout",
    "get_all_stockout_risks",
    "get_customer_intelligence",
    "detect_opportunities",
    "get_business_event",
    "generate_next_best_actions",
    "get_action_outcome",
    "get_action_history",
    "get_financial_opportunities",
    "get_recent_merchant_context",
    "get_recommendation_feedback",
    "get_merchant_feedback_summary",
    "simulate_business_action",
]


