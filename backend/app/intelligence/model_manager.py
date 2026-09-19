import os
import logging
import joblib
from sqlalchemy.orm import Session
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import Ridge

from app.intelligence.config import ANOMALY_MODELS_DIR, DEMAND_MODELS_DIR, ANOMALY_CONTAMINATION
from app.intelligence.data_loader import load_hourly_aggregation
from app.intelligence.preprocessing import resample_hourly_series
from app.intelligence.features import prepare_forecasting_feature_matrix

logger = logging.getLogger("paytm_pulse.intelligence.model_manager")


def ensure_model_dirs():
    """Creates local model storage directories if they do not exist."""
    os.makedirs(ANOMALY_MODELS_DIR, exist_ok=True)
    os.makedirs(DEMAND_MODELS_DIR, exist_ok=True)


def get_anomaly_model_path(merchant_id: str) -> str:
    ensure_model_dirs()
    return os.path.join(ANOMALY_MODELS_DIR, f"isolation_forest_{merchant_id}.joblib")


def get_demand_model_path(merchant_id: str, product_id: str) -> str:
    ensure_model_dirs()
    return os.path.join(DEMAND_MODELS_DIR, f"demand_ridge_{merchant_id}_{product_id}.joblib")


def train_anomaly_model(session: Session, merchant_id: str, days: int = 30, save: bool = True) -> dict:
    """
    Trains and saves an IsolationForest anomaly detection model for a merchant.
    """
    hourly_df = load_hourly_aggregation(session, merchant_id, days=days)
    hourly_df = resample_hourly_series(hourly_df, days=days)

    if len(hourly_df) < 24:
        return {
            "merchant_id": merchant_id,
            "status": "skipped",
            "reason": f"Insufficient data ({len(hourly_df)} hours < 24 hours required)"
        }

    X = hourly_df[["quantity", "revenue", "order_count", "aov"]].fillna(0.0)

    model = IsolationForest(
        n_estimators=100,
        contamination=ANOMALY_CONTAMINATION,
        random_state=42
    )
    model.fit(X)

    if save:
        path = get_anomaly_model_path(merchant_id)
        joblib.dump(model, path)
        logger.info(f"Saved Anomaly model for merchant {merchant_id} to {path}")

    return {
        "merchant_id": merchant_id,
        "status": "trained_and_saved",
        "model_type": "IsolationForest",
        "training_samples": len(X),
        "model_path": get_anomaly_model_path(merchant_id) if save else None
    }


def load_anomaly_model(merchant_id: str):
    """
    Loads saved IsolationForest model if available on disk.
    """
    path = get_anomaly_model_path(merchant_id)
    if os.path.exists(path):
        try:
            return joblib.load(path)
        except Exception as e:
            logger.warning(f"Failed to load anomaly model from {path}: {str(e)}")
    return None


def train_demand_model(session: Session, merchant_id: str, product_id: str, days: int = 30, save: bool = True) -> dict:
    """
    Trains and saves a Ridge regression demand model for a product.
    """
    hourly_df = load_hourly_aggregation(session, merchant_id, product_id=product_id, days=days)
    hourly_df = resample_hourly_series(hourly_df, days=days)

    if len(hourly_df) < 48:
        return {
            "merchant_id": merchant_id,
            "product_id": product_id,
            "status": "skipped",
            "reason": f"Insufficient data ({len(hourly_df)} hours < 48 hours required)"
        }

    X, y = prepare_forecasting_feature_matrix(hourly_df, target_col="quantity")

    model = Ridge(alpha=1.0)
    model.fit(X, y)

    if save:
        path = get_demand_model_path(merchant_id, product_id)
        joblib.dump(model, path)
        logger.info(f"Saved Demand model for merchant {merchant_id}, product {product_id} to {path}")

    return {
        "merchant_id": merchant_id,
        "product_id": product_id,
        "status": "trained_and_saved",
        "model_type": "Ridge_Regression",
        "training_samples": len(X),
        "model_path": get_demand_model_path(merchant_id, product_id) if save else None
    }


def load_demand_model(merchant_id: str, product_id: str):
    """
    Loads saved Demand model if available on disk.
    """
    path = get_demand_model_path(merchant_id, product_id)
    if os.path.exists(path):
        try:
            return joblib.load(path)
        except Exception as e:
            logger.warning(f"Failed to load demand model from {path}: {str(e)}")
    return None
