import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.transaction import Transaction
from app.intelligence.data_loader import load_customer_transactions, load_merchant_sales
from app.intelligence.config import CUSTOMER_INACTIVE_DAYS, CUSTOMER_AT_RISK_DAYS, CUSTOMER_HIGH_VALUE_THRESHOLD
from app.models.base import utc_now

logger = logging.getLogger("paytm_pulse.intelligence.customer_intelligence")


def analyze_merchant_customers(session: Session, merchant_id: str) -> dict:
    """
    Performs customer intelligence, RFM segmentation, and churn risk scoring for a merchant's customer base.
    """
    df = load_customer_transactions(session, merchant_id)
    if df.empty:
        return {
            "merchant_id": merchant_id,
            "total_customers": 0,
            "segments_summary": {
                "HIGH_VALUE": 0, "FREQUENT": 0, "ACTIVE": 0,
                "AT_RISK": 0, "INACTIVE": 0, "NEW": 0
            },
            "customers": []
        }

    now = utc_now()
    customer_list = []
    segment_counts = {
        "HIGH_VALUE": 0, "FREQUENT": 0, "ACTIVE": 0,
        "AT_RISK": 0, "INACTIVE": 0, "NEW": 0
    }

    for _, row in df.iterrows():
        c_id = row["customer_id"]
        spend = float(row["total_spend"])
        p_count = int(row["purchase_count"])
        last_dt = row["last_purchase_at"]
        avg_interval = float(row["average_purchase_interval"]) if row["average_purchase_interval"] else 7.0

        if last_dt is not None and not pd.isna(last_dt):
            days_since = max(0, (now - last_dt).days)
        else:
            days_since = 90

        # RFM Segment Determination
        if p_count == 1 and days_since <= 7:
            segment = "NEW"
        elif spend >= CUSTOMER_HIGH_VALUE_THRESHOLD:
            segment = "HIGH_VALUE"
        elif p_count >= 5 and days_since <= CUSTOMER_INACTIVE_DAYS:
            segment = "FREQUENT"
        elif days_since <= CUSTOMER_INACTIVE_DAYS:
            segment = "ACTIVE"
        elif days_since <= CUSTOMER_AT_RISK_DAYS:
            segment = "AT_RISK"
        else:
            segment = "INACTIVE"

        segment_counts[segment] = segment_counts.get(segment, 0) + 1

        # Churn risk score: Ratio of days_since to (avg_interval * 2) capped at 1.0
        expected_cycle = max(avg_interval * 2.0, 14.0)
        churn_risk = round(float(np.clip(days_since / expected_cycle, 0.05, 0.99)), 2)
        if segment in ["INACTIVE", "AT_RISK"]:
            churn_risk = max(churn_risk, 0.70)

        aov = round(spend / max(p_count, 1), 2)

        customer_list.append({
            "customer_id": c_id,
            "name": row["name"],
            "phone": row["phone"],
            "segment": segment,
            "total_spend": round(spend, 2),
            "purchase_count": p_count,
            "average_order_value": aov,
            "days_since_last_purchase": days_since,
            "average_purchase_interval_days": round(avg_interval, 1),
            "churn_risk_score": churn_risk
        })

    # Sort customers by total spend descending
    customer_list.sort(key=lambda x: x["total_spend"], reverse=True)

    return {
        "merchant_id": merchant_id,
        "total_customers": len(customer_list),
        "segments_summary": segment_counts,
        "customers": customer_list
    }


def get_single_customer_intelligence(session: Session, merchant_id: str, customer_id: str) -> dict:
    """
    Detailed intelligence analysis for an individual customer.
    """
    cust = session.query(Customer).filter(Customer.id == customer_id, Customer.merchant_id == merchant_id).first()
    if not cust:
        return {"error": f"Customer {customer_id} not found for merchant {merchant_id}"}

    all_data = analyze_merchant_customers(session, merchant_id)
    cust_item = next((c for c in all_data["customers"] if c["customer_id"] == customer_id), None)

    return cust_item or {
        "customer_id": customer_id,
        "name": cust.name,
        "phone": cust.phone,
        "segment": "NEW",
        "total_spend": float(cust.total_spend or 0.0),
        "purchase_count": int(cust.purchase_count or 0),
        "average_order_value": 0.0,
        "days_since_last_purchase": 0,
        "average_purchase_interval_days": 7.0,
        "churn_risk_score": 0.10
    }
