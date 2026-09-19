"""
Paytm Pulse - Phase 5 Agent API Endpoints
Provides REST APIs for event analysis, merchant business health reasoning, and conversational chat.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.agent.schemas import (
    AnalyzeEventRequest,
    AnalyzeMerchantRequest,
    AgentAnalysis,
    ChatRequest,
    ChatResponse
)
from app.agent.agent import (
    analyze_business_event,
    analyze_merchant_health,
    chat_with_merchant
)

logger = logging.getLogger("paytm_pulse.api.agent")

router = APIRouter(tags=["Agent - Business Intelligence Reasoning"])


@router.post("/agent/analyze-event", response_model=AgentAnalysis, status_code=status.HTTP_200_OK)
def analyze_event_endpoint(payload: AnalyzeEventRequest, db: Session = Depends(get_db)):
    """
    Reason over a real-time business event using Gemini and Phase 4 intelligence tools.
    Produces structured, non-executing business recommendations with evidence and impact estimates.
    """
    try:
        analysis = analyze_business_event(event_id=payload.event_id, db=db)
        return analysis
    except ValueError as e:
        logger.warning(f"Validation error in analyze_event: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error in analyze_event for event_id '{payload.event_id}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Agent reasoning failed")


@router.post("/agent/analyze-merchant", response_model=AgentAnalysis, status_code=status.HTTP_200_OK)
def analyze_merchant_endpoint(payload: AnalyzeMerchantRequest, db: Session = Depends(get_db)):
    """
    Perform a general business health and opportunity diagnosis for a merchant.
    """
    try:
        analysis = analyze_merchant_health(merchant_id=payload.merchant_id, db=db)
        return analysis
    except ValueError as e:
        logger.warning(f"Validation error in analyze_merchant: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error in analyze_merchant for merchant_id '{payload.merchant_id}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Agent reasoning failed")


@router.post("/agent/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat_endpoint(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Merchant conversational chat grounded in live sales, inventory, customer metrics, and short-term memory.
    """
    try:
        response = chat_with_merchant(
            merchant_id=payload.merchant_id,
            message=payload.message,
            language=payload.language,
            db=db
        )
        return response
    except ValueError as e:
        logger.warning(f"Validation error in chat: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error in chat for merchant_id '{payload.merchant_id}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Agent chat failed")
