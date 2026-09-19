import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services import redis_service
from app.intelligence.config import CACHE_TTL_SECONDS
from app.schemas.intelligence import (
    AnomalyDetectionRequest,
    DemandForecastRequest,
    StockoutPredictionRequest,
    EventAnalysisRequest,
    ModelTrainingRequest
)
from app.intelligence import (
    analyze_merchant_sales,
    analyze_product_demand,
    detect_sales_anomalies,
    detect_product_anomalies,
    forecast_product_demand,
    predict_product_stockout,
    predict_merchant_stockouts,
    analyze_merchant_customers,
    get_single_customer_intelligence,
    detect_merchant_opportunities,
    train_anomaly_model,
    train_demand_model,
    analyze_business_event
)

logger = logging.getLogger("paytm_pulse.api.intelligence")

router = APIRouter(prefix="/intelligence", tags=["ML Business Intelligence"])


def _get_cached_or_compute(cache_key: str, compute_fn, ttl: int = CACHE_TTL_SECONDS):
    """
    Helper to fetch cached JSON from Redis or compute and cache with TTL.
    """
    try:
        client = redis_service.get_redis_client()
        cached = client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.debug(f"Redis cache miss/error for {cache_key}: {str(e)}")

    result = compute_fn()

    try:
        client = redis_service.get_redis_client()
        client.setex(cache_key, ttl, json.dumps(result, default=str))
    except Exception as e:
        logger.debug(f"Redis cache set failed for {cache_key}: {str(e)}")

    return result


@router.get("/sales/{merchant_id}")
def get_merchant_sales_analysis(
    merchant_id: str,
    product_id: Optional[str] = Query(None, description="Optional product ID to get product demand breakdown"),
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Returns multi-horizon deterministic sales analytics for a merchant or product.
    """
    cache_key = f"cache:intelligence:sales:{merchant_id}:{product_id}:{days}"
    if product_id:
        return _get_cached_or_compute(cache_key, lambda: analyze_product_demand(db, merchant_id, product_id, days=days))
    return _get_cached_or_compute(cache_key, lambda: analyze_merchant_sales(db, merchant_id, days=days))


@router.post("/anomaly-detection")
def run_anomaly_detection(
    payload: AnomalyDetectionRequest,
    db: Session = Depends(get_db)
):
    """
    Runs Scikit-learn IsolationForest anomaly detection on merchant or product transaction patterns.
    """
    cache_key = f"cache:intelligence:anomaly:{payload.merchant_id}:{payload.product_id}:{payload.days}"
    if payload.product_id:
        return _get_cached_or_compute(cache_key, lambda: detect_product_anomalies(db, payload.merchant_id, payload.product_id, days=payload.days), ttl=60)
    return _get_cached_or_compute(cache_key, lambda: detect_sales_anomalies(db, payload.merchant_id, days=payload.days), ttl=60)


@router.post("/demand-forecast")
def run_demand_forecast(
    payload: DemandForecastRequest,
    db: Session = Depends(get_db)
):
    """
    Predicts next hour, next 6 hours, and next 24 hours product demand using regression + WMA.
    """
    cache_key = f"cache:intelligence:demand:{payload.merchant_id}:{payload.product_id}:{payload.days}"
    return _get_cached_or_compute(cache_key, lambda: forecast_product_demand(db, payload.merchant_id, payload.product_id, days=payload.days), ttl=120)


@router.post("/stockout-prediction")
def run_stockout_prediction(
    payload: StockoutPredictionRequest,
    db: Session = Depends(get_db)
):
    """
    Calculates estimated hours/minutes to stockout by combining current inventory and forecasted consumption.
    """
    cache_key = f"cache:intelligence:stockout:{payload.merchant_id}:{payload.product_id}"
    if payload.product_id:
        return _get_cached_or_compute(cache_key, lambda: predict_product_stockout(db, payload.merchant_id, payload.product_id), ttl=60)
    return _get_cached_or_compute(cache_key, lambda: predict_merchant_stockouts(db, payload.merchant_id), ttl=60)


@router.get("/customers/{merchant_id}")
def get_customer_intelligence(
    merchant_id: str,
    customer_id: Optional[str] = Query(None, description="Optional customer ID for individual profile"),
    db: Session = Depends(get_db)
):
    """
    Returns RFM customer segmentation (HIGH_VALUE, ACTIVE, AT_RISK, INACTIVE, FREQUENT, NEW) and churn scores.
    """
    cache_key = f"cache:intelligence:customers:{merchant_id}:{customer_id}"
    if customer_id:
        return _get_cached_or_compute(cache_key, lambda: get_single_customer_intelligence(db, merchant_id, customer_id))
    return _get_cached_or_compute(cache_key, lambda: analyze_merchant_customers(db, merchant_id))


@router.get("/opportunities/{merchant_id}")
def get_merchant_opportunities(
    merchant_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns detected business opportunities (DEMAND_GROWTH, RESTOCK, CROSS_SELL, CUSTOMER_WINBACK).
    """
    cache_key = f"cache:intelligence:opportunities:{merchant_id}"
    return _get_cached_or_compute(cache_key, lambda: detect_merchant_opportunities(db, merchant_id), ttl=120)


@router.post("/analyze-event")
def analyze_event(
    payload: EventAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Enriches a Phase 3 BusinessEvent with deep ML Intelligence (baseline, anomaly score, forecast, stockout risk, revenue exposure).
    """
    result = analyze_business_event(db, payload.event_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.post("/train-models")
def train_models_endpoint(
    payload: ModelTrainingRequest,
    db: Session = Depends(get_db)
):
    """
    Explicit model training endpoint: trains and persists Joblib models for IsolationForest and Demand Ridge Regression.
    """
    results = {}
    if payload.model_type in ["all", "anomaly"]:
        results["anomaly_model"] = train_anomaly_model(db, payload.merchant_id, days=payload.days, save=True)

    if payload.model_type in ["all", "demand"] and payload.product_id:
        results["demand_model"] = train_demand_model(db, payload.merchant_id, payload.product_id, days=payload.days, save=True)

    return {
        "status": "success",
        "merchant_id": payload.merchant_id,
        "results": results
    }
