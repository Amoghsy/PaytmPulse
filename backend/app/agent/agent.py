"""
Paytm Pulse - Phase 5 AI Business Partner Agent Entrypoints
High-level service interface for event reasoning, merchant diagnosis, and conversational chat.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.agent.runner import AgentRunner
from app.agent.schemas import AgentAnalysis, ChatResponse


def analyze_business_event(event_id: str, db: Optional[Session] = None) -> AgentAnalysis:
    """
    Analyzes a real-time business event using Gemini / Phase 4 intelligence tools.
    
    Args:
        event_id: ID of the BusinessEvent.
        db: Optional active SQLAlchemy session.
        
    Returns:
        Structured AgentAnalysis recommendation.
    """
    if db is not None:
        runner = AgentRunner(db)
        return runner.run_event_analysis(event_id)
    else:
        with get_db_context() as session:
            runner = AgentRunner(session)
            return runner.run_event_analysis(event_id)


def analyze_merchant_health(merchant_id: str, db: Optional[Session] = None) -> AgentAnalysis:
    """
    Performs comprehensive business health and opportunity reasoning for a merchant.
    
    Args:
        merchant_id: Unique merchant ID.
        db: Optional active SQLAlchemy session.
        
    Returns:
        Structured AgentAnalysis recommendation.
    """
    if db is not None:
        runner = AgentRunner(db)
        return runner.run_merchant_analysis(merchant_id)
    else:
        with get_db_context() as session:
            runner = AgentRunner(session)
            return runner.run_merchant_analysis(merchant_id)


def chat_with_merchant(
    merchant_id: str,
    message: str,
    language: Optional[str] = None,
    db: Optional[Session] = None
) -> ChatResponse:
    """
    Engages in conversational chat with the merchant grounded in live metrics and conversational context.
    
    Args:
        merchant_id: Unique merchant ID.
        message: Natural language query from merchant.
        language: Optional target language code or name ('en', 'kn', 'hi', 'mr').
        db: Optional active SQLAlchemy session.
        
    Returns:
        ChatResponse with natural language answer and supporting data.
    """
    if db is not None:
        runner = AgentRunner(db)
        return runner.run_chat(merchant_id, message, language=language)
    else:
        with get_db_context() as session:
            runner = AgentRunner(session)
            return runner.run_chat(merchant_id, message, language=language)
