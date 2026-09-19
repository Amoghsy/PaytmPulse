import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.connection import get_db, check_database_connection, engine
from app.models import (
    Base, Merchant, Product, Customer, Transaction,
    BusinessEvent, Recommendation, Action, Outcome
)
from app.database.seed import seed_data

logger = logging.getLogger("paytm_pulse.system")

router = APIRouter(prefix="/system", tags=["System"])


@router.post("/seed", summary="Seed Presentation Demo Data")
def seed_system_data(clear_existing: bool = False):
    """
    Seeds rich demo data (Merchants, Products, Transactions, Events, Recommendations, Actions, Outcomes)
    into the active database (Supabase/Postgres).
    """
    try:
        # Ensure schema tables exist first
        Base.metadata.create_all(bind=engine)
        seed_data(clear_existing=clear_existing)
        return {
            "status": "success",
            "message": "Paytm Pulse presentation demo data successfully seeded!"
        }
    except Exception as e:
        logger.error(f"Failed to seed demo data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "SEEDING_FAILED", "message": str(e)}}
        )


@router.get("/overview", summary="Get Presentation Dashboard Overview")
def get_system_overview(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns high-level aggregate KPI statistics across all 13 phases for the executive dashboard.
    """
    try:
        merchants_count = db.query(Merchant).count()
        products_count = db.query(Product).count()
        customers_count = db.query(Customer).count()
        transactions_count = db.query(Transaction).count()
        
        revenue_val = db.query(func.sum(Transaction.amount)).scalar()
        total_revenue = float(revenue_val or 0.0)

        events_count = db.query(BusinessEvent).count()
        recommendations_count = db.query(Recommendation).count()
        actions_count = db.query(Action).count()
        outcomes_count = db.query(Outcome).count()

        return {
            "status": "healthy",
            "metrics": {
                "merchants": merchants_count,
                "products": products_count,
                "customers": customers_count,
                "transactions": transactions_count,
                "total_revenue": total_revenue,
                "events_detected": events_count,
                "recommendations_generated": recommendations_count,
                "actions_executed": actions_count,
                "measured_outcomes": outcomes_count
            }
        }
    except Exception as e:
        logger.error(f"Error querying live system overview from database: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "metrics": {
                "merchants": 0,
                "products": 0,
                "customers": 0,
                "transactions": 0,
                "total_revenue": 0.0,
                "events_detected": 0,
                "recommendations_generated": 0,
                "actions_executed": 0,
                "measured_outcomes": 0
            }
        }
