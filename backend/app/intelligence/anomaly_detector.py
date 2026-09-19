import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sklearn.ensemble import IsolationForest

from app.intelligence.data_loader import load_product_sales, load_hourly_aggregation
from app.intelligence.preprocessing import resample_hourly_series
from app.intelligence.config import ANOMALY_CONTAMINATION, ANOMALY_SPIKE_RATIO
from app.models.base import utc_now

logger = logging.getLogger("paytm_pulse.intelligence.anomaly_detector")


def detect_sales_anomalies(session: Session, merchant_id: str, days: int = 30) -> dict:
    """
    Detects business and transaction volume anomalies for a merchant using IsolationForest with baseline fallback.
    """
    hourly_df = load_hourly_aggregation(session, merchant_id, days=days)
    hourly_df = resample_hourly_series(hourly_df, days=days)

    if len(hourly_df) < 24:
        return _deterministic_fallback_anomaly(hourly_df, merchant_id)

    # Prepare features for Isolation Forest
    X = hourly_df[["quantity", "revenue", "order_count", "aov"]].copy()

    # Handle NaNs or zeros
    X = X.fillna(0.0)

    try:
        model = IsolationForest(
            n_estimators=100,
            contamination=ANOMALY_CONTAMINATION,
            random_state=42
        )
        model.fit(X)
        scores = model.decision_function(X)
        preds = model.predict(X)  # -1 = anomaly, 1 = normal

        # Check latest hour or past 3 hours
        recent_window = hourly_df.tail(3)
        recent_preds = preds[-3:]
        recent_scores = scores[-3:]

        has_anomaly = bool(np.any(recent_preds == -1))
        latest_row = hourly_df.iloc[-1]
        baseline_revenue = float(hourly_df["revenue"].median())
        baseline_qty = float(hourly_df["quantity"].median())

        observed_revenue = float(latest_row["revenue"])
        observed_qty = float(latest_row["quantity"])

        if has_anomaly or (observed_qty > 0 and observed_qty >= ANOMALY_SPIKE_RATIO * max(baseline_qty, 1.0)):
            # Determine anomaly type
            if observed_qty > baseline_qty * ANOMALY_SPIKE_RATIO:
                anom_type = "DEMAND_SPIKE"
            elif observed_revenue < baseline_revenue * 0.30:
                anom_type = "SALES_DROP"
            elif float(latest_row["aov"]) > float(hourly_df["aov"].quantile(0.95)):
                anom_type = "TICKET_SIZE_ANOMALY"
            else:
                anom_type = "UNUSUAL_VOLUME"

            # Confidence derived from normalized IsolationForest decision score or deviation ratio
            min_score = float(np.min(recent_scores)) if len(recent_scores) > 0 else -0.1
            confidence = round(float(np.clip(0.5 + abs(min_score) * 2.0, 0.50, 0.98)), 2)

            severity = "CRITICAL" if confidence >= 0.90 else "HIGH" if confidence >= 0.75 else "MEDIUM"

            return {
                "merchant_id": merchant_id,
                "anomaly_detected": True,
                "anomaly_type": anom_type,
                "severity": severity,
                "confidence": confidence,
                "affected_product": "All Products",
                "observed_value": observed_qty if anom_type == "DEMAND_SPIKE" else observed_revenue,
                "baseline_value": baseline_qty if anom_type == "DEMAND_SPIKE" else baseline_revenue,
                "details": {
                    "latest_hour_orders": int(latest_row["order_count"]),
                    "latest_hour_revenue": observed_revenue,
                    "latest_hour_quantity": observed_qty,
                    "baseline_hourly_revenue": round(baseline_revenue, 2),
                    "baseline_hourly_quantity": round(baseline_qty, 2),
                    "method": "IsolationForest_ML"
                }
            }

        return {
            "merchant_id": merchant_id,
            "anomaly_detected": False,
            "anomaly_type": None,
            "severity": "LOW",
            "confidence": 0.95,
            "affected_product": None,
            "observed_value": observed_revenue,
            "baseline_value": baseline_revenue,
            "details": {"method": "IsolationForest_ML", "status": "nominal"}
        }

    except Exception as e:
        logger.warning(f"Isolation Forest execution failed for merchant {merchant_id}: {str(e)}. Falling back to baseline.")
        return _deterministic_fallback_anomaly(hourly_df, merchant_id)


def detect_product_anomalies(session: Session, merchant_id: str, product_id: str, days: int = 30) -> dict:
    """
    Detects unusual spike or drop for a single product.
    """
    prod_sales = load_product_sales(session, merchant_id, product_id=product_id, days=days)
    if prod_sales.empty:
        return {
            "merchant_id": merchant_id,
            "product_id": product_id,
            "anomaly_detected": False,
            "anomaly_type": None,
            "severity": "LOW",
            "confidence": 0.50,
            "observed_value": 0,
            "baseline_value": 0
        }

    prod_name = prod_sales["product_name"].iloc[0] if "product_name" in prod_sales.columns else "Product"
    hourly_df = load_hourly_aggregation(session, merchant_id, product_id=product_id, days=days)
    hourly_df = resample_hourly_series(hourly_df, days=days)

    baseline_qty = float(hourly_df["quantity"].mean())
    recent_qty = float(hourly_df.tail(3)["quantity"].sum()) / 3.0

    if baseline_qty > 0 and recent_qty >= ANOMALY_SPIKE_RATIO * baseline_qty and recent_qty >= 3.0:
        ratio = round(recent_qty / max(baseline_qty, 1.0), 2)
        confidence = round(float(np.clip(0.65 + (ratio * 0.08), 0.70, 0.96)), 2)
        severity = "CRITICAL" if ratio >= 3.0 else "HIGH"

        return {
            "merchant_id": merchant_id,
            "product_id": product_id,
            "product_name": prod_name,
            "anomaly_detected": True,
            "anomaly_type": "DEMAND_SPIKE",
            "severity": severity,
            "confidence": confidence,
            "affected_product": prod_name,
            "observed_value": round(recent_qty, 1),
            "baseline_value": round(baseline_qty, 1),
            "details": {
                "spike_ratio": ratio,
                "message": f"Unusual demand surge for '{prod_name}': {round(recent_qty, 1)} units/hr vs baseline {round(baseline_qty, 1)} units/hr ({ratio}x)."
            }
        }

    return {
        "merchant_id": merchant_id,
        "product_id": product_id,
        "product_name": prod_name,
        "anomaly_detected": False,
        "anomaly_type": None,
        "severity": "LOW",
        "confidence": 0.90,
        "observed_value": round(recent_qty, 1),
        "baseline_value": round(baseline_qty, 1),
        "details": {"status": "normal_demand"}
    }


def _deterministic_fallback_anomaly(hourly_df: pd.DataFrame, merchant_id: str) -> dict:
    """
    Robust non-ML statistical baseline comparison for cold start / limited historical rows.
    """
    if hourly_df.empty:
        return {
            "merchant_id": merchant_id,
            "anomaly_detected": False,
            "anomaly_type": None,
            "severity": "LOW",
            "confidence": 0.50,
            "observed_value": 0.0,
            "baseline_value": 0.0,
            "details": {"method": "fallback_insufficient_data"}
        }

    median_qty = float(hourly_df["quantity"].median())
    last_qty = float(hourly_df["quantity"].iloc[-1]) if not hourly_df.empty else 0.0

    if median_qty > 0 and last_qty >= ANOMALY_SPIKE_RATIO * median_qty:
        return {
            "merchant_id": merchant_id,
            "anomaly_detected": True,
            "anomaly_type": "DEMAND_SPIKE",
            "severity": "MEDIUM",
            "confidence": 0.70,
            "affected_product": "All Products",
            "observed_value": last_qty,
            "baseline_value": median_qty,
            "details": {"method": "statistical_baseline_fallback"}
        }

    return {
        "merchant_id": merchant_id,
        "anomaly_detected": False,
        "anomaly_type": None,
        "severity": "LOW",
        "confidence": 0.80,
        "observed_value": last_qty,
        "baseline_value": median_qty,
        "details": {"method": "statistical_baseline_fallback"}
    }
