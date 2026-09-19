import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.financial.recommendation_service import FinancialRecommendationService
from app.financial.schemas import (
    FinancialProductResponse,
    FinancialOpportunityResponse,
    FinancialRecommendationResponse,
    MerchantInterestRequest,
    MerchantDeclineRequest
)

logger = logging.getLogger("paytm_pulse.api.financial")

router = APIRouter(prefix="/financial", tags=["Financial Products (Simulated)"])


@router.get(
    "/products",
    response_model=List[FinancialProductResponse],
    summary="Get Simulated Financial Product Catalog",
    description="Retrieve the active catalog of contextual simulated financial products (Working Capital, Inventory Financing, Business Expansion, Cash Flow Support)."
)
def get_financial_products(db: Session = Depends(get_db)):
    service = FinancialRecommendationService(db)
    return service.get_catalog()


@router.get(
    "/opportunities/{merchant_id}",
    response_model=FinancialOpportunityResponse,
    summary="Get Financial Opportunities for Merchant",
    description="Detects whether the merchant currently exhibits operational signals (demand surge, restocking frequency) that match a simulated financial product."
)
def get_merchant_opportunities(merchant_id: str, db: Session = Depends(get_db)):
    service = FinancialRecommendationService(db)
    return service.get_merchant_opportunities(merchant_id)


@router.post(
    "/analyze/{merchant_id}",
    response_model=FinancialOpportunityResponse,
    summary="Analyze Merchant Signals & Recommend Financial Product",
    description="Runs deterministic signal evaluation. If an opportunity is detected and not under cooldown, creates a persistent recommendation."
)
def analyze_merchant_financial_signals(
    merchant_id: str,
    bypass_cooldown: bool = Query(False, description="Bypass cooldown for demo/testing"),
    db: Session = Depends(get_db)
):
    service = FinancialRecommendationService(db)
    return service.analyze_and_recommend(merchant_id, bypass_cooldown=bypass_cooldown)


@router.get(
    "/recommendations/{merchant_id}",
    response_model=List[FinancialRecommendationResponse],
    summary="Get Merchant Financial Recommendations",
    description="Retrieve historical contextual financial product recommendations generated for this merchant."
)
def get_merchant_recommendations(
    merchant_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    service = FinancialRecommendationService(db)
    return service.get_merchant_recommendations(merchant_id, limit=limit)


@router.get(
    "/recommendation/{recommendation_id}",
    response_model=FinancialRecommendationResponse,
    summary="Get Financial Recommendation by ID",
    description="Retrieve specific financial recommendation details."
)
def get_recommendation_details(recommendation_id: str, db: Session = Depends(get_db)):
    service = FinancialRecommendationService(db)
    rec = service.get_recommendation_by_id(recommendation_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Financial recommendation '{recommendation_id}' not found."
        )
    return rec


@router.post(
    "/recommendations/{recommendation_id}/interest",
    response_model=FinancialRecommendationResponse,
    summary="Record Merchant Interest",
    description="Transitions recommendation status to INTERESTED without initiating real loan underwriting or financial transactions."
)
def express_merchant_interest(
    recommendation_id: str,
    payload: Optional[MerchantInterestRequest] = None,
    db: Session = Depends(get_db)
):
    service = FinancialRecommendationService(db)
    try:
        notes = payload.notes if payload else None
        return service.record_merchant_interest(recommendation_id, notes=notes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/recommendations/{recommendation_id}/decline",
    response_model=FinancialRecommendationResponse,
    summary="Record Merchant Decline",
    description="Transitions recommendation status to DECLINED."
)
def decline_merchant_recommendation(
    recommendation_id: str,
    payload: Optional[MerchantDeclineRequest] = None,
    db: Session = Depends(get_db)
):
    service = FinancialRecommendationService(db)
    try:
        reason = payload.reason if payload else None
        return service.record_merchant_decline(recommendation_id, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
