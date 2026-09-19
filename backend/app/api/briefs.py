"""
Paytm Pulse - AI Daily Business Brief REST API Endpoints
Provides endpoints for n8n workflow orchestration, Gemini generative summarization,
idempotent brief storage, latest dashboard retrieval, and WhatsApp notification delivery.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database.connection import get_db
from app.models.merchant import Merchant
from app.models.business_brief import BusinessBrief
from app.schemas.brief import (
    MerchantBriefContext,
    GenerateBriefRequest,
    StoreBriefRequest,
    SendWhatsAppBriefRequest,
    BusinessBriefOut
)
from app.services.brief_service import (
    collect_merchant_brief_context,
    generate_brief_with_gemini,
    store_business_brief,
    get_latest_brief,
    send_brief_whatsapp_notification,
    _get_current_date_str
)

logger = logging.getLogger("paytm_pulse.api.briefs")

router = APIRouter(tags=["AI Daily Business Briefs"])


@router.get("/briefs/merchants", summary="Get Active Merchants for Daily Briefs")
def get_active_merchants_for_briefs(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Returns list of active merchants with compact, privacy-safe metadata for the daily brief workflow.
    """
    merchants = db.query(Merchant).order_by(Merchant.created_at.asc()).limit(limit).all()
    results = []
    for m in merchants:
        results.append({
            "id": m.id,
            "name": m.name,
            "shop_name": m.shop_name or m.business_name or "Store",
            "category": m.category.value if hasattr(m.category, "value") else str(m.category),
            "location": m.location,
            "language": m.language or "English",
            "phone": m.phone
        })
    return results


@router.get("/briefs/{merchant_id}/context", response_model=MerchantBriefContext, summary="Get Structured Brief Context")
def get_merchant_brief_context_endpoint(
    merchant_id: str,
    db: Session = Depends(get_db)
):
    """
    Consolidates multi-horizon business telemetry (Sales, Stockouts, Customers, Opportunities, Events)
    into a structured context object for Gemini AI summarization.
    """
    try:
        context = collect_merchant_brief_context(merchant_id=merchant_id, db=db)
        return context
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error collecting brief context for merchant '{merchant_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to collect merchant context")


@router.post("/briefs/generate", response_model=BusinessBriefOut, summary="Generate and Store Daily Business Brief")
def generate_and_store_brief_endpoint(
    payload: GenerateBriefRequest,
    db: Session = Depends(get_db)
):
    """
    Gathers merchant context, invokes Gemini AI summarizer with strict guardrails (or deterministic fallback),
    and idempotently saves the brief in PostgreSQL and Redis.
    """
    try:
        context = collect_merchant_brief_context(merchant_id=payload.merchant_id, db=db)
        target_lang = payload.language or context.get("merchant", {}).get("language") or "English"
        brief_date = payload.brief_date or _get_current_date_str()

        # Check if already generated today and force_refresh is not requested
        if not payload.force_refresh:
            existing = db.query(BusinessBrief)\
                .filter_by(merchant_id=payload.merchant_id, brief_date=brief_date)\
                .first()
            if existing:
                return existing

        brief_content, source = generate_brief_with_gemini(context=context, language=target_lang)

        stored = store_business_brief(
            merchant_id=payload.merchant_id,
            brief_content=brief_content,
            brief_date=brief_date,
            generated_by=source,
            language=target_lang,
            db=db
        )
        return stored
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating brief for merchant '{payload.merchant_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate brief: {str(e)}")


@router.post("/briefs", response_model=BusinessBriefOut, status_code=status.HTTP_201_CREATED, summary="Store Business Brief (n8n node)")
def store_brief_endpoint(
    payload: StoreBriefRequest,
    db: Session = Depends(get_db)
):
    """
    Direct endpoint for n8n workflow or backend services to persist validated brief content with daily idempotency.
    """
    try:
        stored = store_business_brief(
            merchant_id=payload.merchant_id,
            brief_content=payload.brief,
            brief_date=payload.brief_date,
            generated_by=payload.generated_by or "gemini",
            language=payload.language or "en",
            db=db
        )
        return stored
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error storing brief: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store brief")


@router.get("/briefs/{merchant_id}/latest", response_model=BusinessBriefOut, summary="Get Latest Business Brief for Dashboard")
def get_latest_brief_endpoint(
    merchant_id: str,
    auto_generate: bool = Query(True, description="Auto-generate today's brief if not found"),
    db: Session = Depends(get_db)
):
    """
    Retrieves the latest available daily brief for the merchant dashboard.
    If no brief exists and auto_generate is True, synthesizes today's brief on demand.
    """
    brief = get_latest_brief(merchant_id=merchant_id, db=db)
    if brief:
        return brief

    if auto_generate:
        try:
            context = collect_merchant_brief_context(merchant_id=merchant_id, db=db)
            target_lang = context.get("merchant", {}).get("language") or "English"
            brief_content, source = generate_brief_with_gemini(context=context, language=target_lang)
            stored = store_business_brief(
                merchant_id=merchant_id,
                brief_content=brief_content,
                brief_date=_get_current_date_str(),
                generated_by=source,
                language=target_lang,
                db=db
            )
            return stored
        except Exception as e:
            logger.error(f"Failed to auto-generate initial brief for '{merchant_id}': {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No business brief found for merchant '{merchant_id}'"
    )


@router.get("/briefs/{merchant_id}/history", response_model=List[BusinessBriefOut], summary="Get Brief History")
def get_brief_history_endpoint(
    merchant_id: str,
    limit: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Retrieves historical business briefs for a merchant sorted by date descending.
    """
    briefs = db.query(BusinessBrief)\
        .filter_by(merchant_id=merchant_id)\
        .order_by(desc(BusinessBrief.brief_date), desc(BusinessBrief.created_at))\
        .limit(limit)\
        .all()
    return briefs


@router.post("/briefs/{merchant_id}/send-whatsapp", summary="Send Brief over WhatsApp")
def send_whatsapp_brief_endpoint(
    merchant_id: str,
    payload: Optional[SendWhatsAppBriefRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Dispatches the latest morning business brief to the merchant's WhatsApp in their preferred language.
    """
    brief = get_latest_brief(merchant_id=merchant_id, db=db)
    if not brief:
        # Generate on the fly
        try:
            context = collect_merchant_brief_context(merchant_id=merchant_id, db=db)
            target_lang = context.get("merchant", {}).get("language") or "English"
            brief_content, source = generate_brief_with_gemini(context=context, language=target_lang)
            brief = store_business_brief(
                merchant_id=merchant_id,
                brief_content=brief_content,
                brief_date=_get_current_date_str(),
                generated_by=source,
                language=target_lang,
                db=db
            )
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No brief available to send: {e}")

    custom_msg = payload.custom_message if payload else None
    result = send_brief_whatsapp_notification(merchant_id=merchant_id, brief=brief, db=db, custom_message=custom_msg)
    return result
