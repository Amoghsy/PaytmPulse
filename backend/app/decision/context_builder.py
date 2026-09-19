"""
Paytm Pulse - Phase 6 Decision Context Builder
Aggregates merchant data, inventory levels, Phase 4 ML intelligence, and Phase 5 agent reasoning.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.merchant import Merchant
from app.models.product import Product
from app.models.business_event import BusinessEvent
from app.agent.tools.sales_tools import get_sales_analysis
from app.agent.tools.inventory_tools import get_all_stockout_risks, predict_stockout
from app.agent.tools.customer_tools import get_customer_intelligence
from app.agent.tools.opportunity_tools import detect_opportunities
from app.agent.tools.event_tools import get_business_event
from app.agent.tools.forecast_tools import forecast_demand


class DecisionContext:
    """Encapsulates all operational and intelligence context needed for action evaluation."""

    def __init__(
        self,
        merchant_id: str,
        merchant: Merchant,
        event: Optional[Dict[str, Any]],
        sales_analysis: Dict[str, Any],
        stockout_risks: Dict[str, Any],
        customer_intelligence: Dict[str, Any],
        opportunities: Dict[str, Any],
        products_map: Dict[str, Product],
        db: Optional[Session] = None
    ):
        self.merchant_id = merchant_id
        self.merchant = merchant
        self.event = event
        self.sales = sales_analysis
        self.stockout_risks = stockout_risks
        self.customers = customer_intelligence
        self.opportunities = opportunities
        self.products = products_map
        self.db = db


def build_decision_context(
    merchant_id: str,
    event_id: Optional[str] = None,
    db: Optional[Session] = None
) -> DecisionContext:
    """
    Builds a complete, queryable DecisionContext from database records and Phase 4 intelligence tools.
    """
    if db is None:
        raise ValueError("Database session is required to build decision context.")

    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise ValueError(f"Merchant '{merchant_id}' not found.")

    # Products Map
    products = db.query(Product).filter(
        Product.merchant_id == merchant_id,
        Product.is_active == True
    ).all()
    products_map = {str(p.id): p for p in products}

    # Inspect Event if present
    event_data = None
    if event_id:
        event_data = get_business_event(event_id, db=db)

    # Gather Intelligence Tools
    sales_data = get_sales_analysis(merchant_id, db=db)
    stockout_data = get_all_stockout_risks(merchant_id, db=db)
    customer_data = get_customer_intelligence(merchant_id, db=db)
    opportunities_data = detect_opportunities(merchant_id, db=db)

    return DecisionContext(
        merchant_id=merchant_id,
        merchant=merchant,
        event=event_data,
        sales_analysis=sales_data,
        stockout_risks=stockout_data,
        customer_intelligence=customer_data,
        opportunities=opportunities_data,
        products_map=products_map,
        db=db
    )
