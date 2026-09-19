import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.feedback.service import FeedbackService


def get_recommendation_feedback(recommendation_id: str, db: Optional[Session] = None) -> str:
    """
    Retrieve full lifecycle feedback and measured effectiveness for a specific recommendation ID.
    Returns status, approval state, execution state, business impact, and merchant rating.
    """
    def _execute(session: Session) -> str:
        service = FeedbackService(session)
        eff = service.get_recommendation_effectiveness(recommendation_id)
        if not eff:
            return json.dumps({
                "status": "NOT_FOUND",
                "message": f"No recommendation found for ID '{recommendation_id}'."
            })

        return json.dumps(eff.model_dump(mode="json"), indent=2)

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)


def get_merchant_feedback_summary(merchant_id: str, db: Optional[Session] = None) -> str:
    """
    Retrieve aggregate feedback and historical effectiveness summary for a merchant.
    Answers whether recommendations have worked for this shop (approval rate, success rate, net revenue).
    """
    def _execute(session: Session) -> str:
        service = FeedbackService(session)
        summary = service.get_merchant_summary(merchant_id)
        return json.dumps(summary.model_dump(mode="json"), indent=2)

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)
