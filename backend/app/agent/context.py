"""
Paytm Pulse - Phase 5 Merchant Context Builder
Assembles concise, targeted merchant profile and operational context for LLM reasoning.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.models.merchant import Merchant
from app.models.product import Product
from app.models.business_event import BusinessEvent


def build_merchant_context(
    merchant_id: str,
    db: Optional[Session] = None,
    include_recent_events: bool = True
) -> Dict[str, Any]:
    """
    Constructs a concise, structured merchant context snapshot.
    
    Args:
        merchant_id: Unique merchant ID.
        db: Optional active SQLAlchemy session.
        include_recent_events: Whether to include recent business events.
        
    Returns:
        Structured context dictionary containing merchant profile, product catalog snapshot,
        and recent event triggers.
    """
    def _execute(session: Session) -> Dict[str, Any]:
        merchant = session.query(Merchant).filter(Merchant.id == merchant_id).first()
        if not merchant:
            return {
                "merchant_id": merchant_id,
                "found": False,
                "error": f"Merchant '{merchant_id}' not found"
            }

        # Catalog snapshot: Top active products with inventory status
        products = session.query(Product).filter(
            Product.merchant_id == merchant_id,
            Product.is_active == True
        ).all()

        catalog_summary: List[Dict[str, Any]] = []
        low_stock_items: List[str] = []
        for p in products:
            catalog_summary.append({
                "product_id": str(p.id),
                "name": p.name,
                "category": p.category,
                "price": float(p.price),
                "current_stock": p.current_stock,
                "reorder_level": p.reorder_level,
                "is_low_stock": p.current_stock <= p.reorder_level
            })
            if p.current_stock <= p.reorder_level:
                low_stock_items.append(p.name)

        # Recent business events
        recent_events_summary: List[Dict[str, Any]] = []
        if include_recent_events:
            events = session.query(BusinessEvent).filter(
                BusinessEvent.merchant_id == merchant_id
            ).order_by(BusinessEvent.detected_at.desc()).limit(5).all()

            for ev in events:
                recent_events_summary.append({
                    "event_id": str(ev.id),
                    "event_type": str(ev.event_type.value if hasattr(ev.event_type, "value") else ev.event_type),
                    "severity": str(ev.severity.value if hasattr(ev.severity, "value") else ev.severity),
                    "detected_at": ev.detected_at.isoformat() if ev.detected_at else None
                })

        category_val = merchant.category.value if hasattr(merchant.category, "value") else str(merchant.category)

        return {
            "merchant_id": str(merchant.id),
            "found": True,
            "merchant_name": merchant.name,
            "shop_name": merchant.shop_name,
            "category": category_val,
            "location": merchant.location,
            "language": merchant.language,
            "total_products_count": len(products),
            "low_stock_products_count": len(low_stock_items),
            "low_stock_items": low_stock_items[:5],
            "catalog_snapshot": catalog_summary[:10],
            "recent_events": recent_events_summary
        }

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)
