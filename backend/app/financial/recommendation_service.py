import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.financial_product import FinancialProduct
from app.models.financial_recommendation import FinancialRecommendation, FinancialRecommendationStatus
from app.financial.config import (
    SIMULATED_FINANCIAL_PRODUCTS,
    FINANCIAL_RECOMMENDATION_COOLDOWN_DAYS
)
from app.financial.schemas import (
    FinancialProductResponse,
    FinancialNeedDetectionResult,
    FinancialRecommendationResponse,
    FinancialOpportunityResponse,
    FinancialNeedType
)
from app.financial.need_detector import FinancialNeedDetector
from app.financial.product_matcher import ProductMatcher
from app.services.redis_service import get_redis_client

logger = logging.getLogger("paytm_pulse.financial.service")


class FinancialRecommendationService:
    """
    Coordinates financial product catalog management, need detection, cooldown rules,
    recommendation persistence, and merchant interest lifecycle.
    """

    def __init__(self, db: Session):
        self.db = db
        self.need_detector = FinancialNeedDetector(db)
        self.product_matcher = ProductMatcher(db)

    def seed_catalog_if_empty(self):
        """
        Seeds standard simulated products into the database if the catalog is empty.
        """
        count = self.db.query(func.count(FinancialProduct.id)).scalar() or 0
        if count == 0:
            for item in SIMULATED_FINANCIAL_PRODUCTS:
                prod = FinancialProduct(**item)
                self.db.add(prod)
            self.db.commit()
            logger.info("Seeded standard simulated financial products catalog.")

    def get_catalog(self) -> List[FinancialProductResponse]:
        """
        Retrieves all active simulated financial products.
        """
        self.seed_catalog_if_empty()
        products = self.db.query(FinancialProduct).filter(FinancialProduct.active == True).all()
        return [FinancialProductResponse.model_validate(p) for p in products]

    def is_in_cooldown(self, merchant_id: str, need_type: str) -> bool:
        """
        Verifies if a recommendation for this need type is currently under cooldown.
        """
        # 1. Redis Check
        try:
            r = get_redis_client()
            if r:
                key = f"cooldown:financial_rec:{merchant_id}:{need_type}"
                if r.get(key):
                    return True
        except Exception as e:
            logger.warning(f"Redis cooldown check error: {e}")

        # 2. Database Check
        lookback = datetime.now(timezone.utc) - timedelta(days=FINANCIAL_RECOMMENDATION_COOLDOWN_DAYS)
        recent = self.db.query(FinancialRecommendation).filter(
            FinancialRecommendation.merchant_id == merchant_id,
            FinancialRecommendation.need_type == need_type,
            FinancialRecommendation.created_at >= lookback
        ).first()

        return recent is not None

    def set_cooldown(self, merchant_id: str, need_type: str):
        """
        Sets Redis cooldown key.
        """
        try:
            r = get_redis_client()
            if r:
                key = f"cooldown:financial_rec:{merchant_id}:{need_type}"
                ttl = FINANCIAL_RECOMMENDATION_COOLDOWN_DAYS * 86400
                r.set(key, "1", ex=ttl)
        except Exception as e:
            logger.warning(f"Failed to set redis cooldown for {merchant_id}:{need_type}: {e}")

    def analyze_and_recommend(
        self,
        merchant_id: str,
        bypass_cooldown: bool = False
    ) -> FinancialOpportunityResponse:
        """
        Analyzes merchant business metrics, detects financial needs, and generates
        a contextual simulated recommendation if eligible.
        """
        self.seed_catalog_if_empty()
        need = self.need_detector.detect_financial_need(merchant_id)

        if not need.need_detected or not need.need_type:
            return FinancialOpportunityResponse(
                merchant_id=merchant_id,
                opportunity_detected=False,
                need_result=need,
                matched_product=None,
                recommendation=None,
                message="No financial opportunities detected based on current business metrics."
            )

        need_type_str = need.need_type.value if hasattr(need.need_type, "value") else str(need.need_type)

        # Check Cooldown
        if not bypass_cooldown and self.is_in_cooldown(merchant_id, need_type_str):
            latest = self.db.query(FinancialRecommendation).filter(
                FinancialRecommendation.merchant_id == merchant_id,
                FinancialRecommendation.need_type == need_type_str
            ).order_by(FinancialRecommendation.created_at.desc()).first()

            if latest:
                return FinancialOpportunityResponse(
                    merchant_id=merchant_id,
                    opportunity_detected=True,
                    need_result=need,
                    matched_product=FinancialProductResponse.model_validate(latest.product) if latest.product else None,
                    recommendation=self._build_recommendation_response(latest),
                    message=f"Opportunity detected (under cooldown period): {latest.title}"
                )

        # Match Product
        product, sim_amount, duration, title = self.product_matcher.match_product(need)
        if not product:
            return FinancialOpportunityResponse(
                merchant_id=merchant_id,
                opportunity_detected=False,
                need_result=need,
                matched_product=None,
                recommendation=None,
                message="Need detected but no matching active product found."
            )

        # Persist Recommendation
        rec = FinancialRecommendation(
            merchant_id=merchant_id,
            product_id=product.id,
            need_type=need_type_str,
            title=title,
            reason=need.reason,
            supporting_signals=need.supporting_signals,
            confidence=need.confidence,
            simulated_amount=sim_amount,
            duration_days=duration,
            status=FinancialRecommendationStatus.RECOMMENDED
        )
        self.db.add(rec)
        self.db.commit()
        self.db.refresh(rec)

        self.set_cooldown(merchant_id, need_type_str)
        logger.info(f"Generated financial recommendation '{rec.title}' for merchant {merchant_id}")

        return FinancialOpportunityResponse(
            merchant_id=merchant_id,
            opportunity_detected=True,
            need_result=need,
            matched_product=FinancialProductResponse.model_validate(product),
            recommendation=self._build_recommendation_response(rec),
            message=f"Contextual opportunity identified: {rec.title}"
        )

    def get_merchant_opportunities(self, merchant_id: str) -> FinancialOpportunityResponse:
        return self.analyze_and_recommend(merchant_id, bypass_cooldown=False)

    def get_merchant_recommendations(self, merchant_id: str, limit: int = 20) -> List[FinancialRecommendationResponse]:
        recs = self.db.query(FinancialRecommendation).filter(
            FinancialRecommendation.merchant_id == merchant_id
        ).order_by(FinancialRecommendation.created_at.desc()).limit(limit).all()

        return [self._build_recommendation_response(r) for r in recs]

    def get_recommendation_by_id(self, recommendation_id: str) -> Optional[FinancialRecommendationResponse]:
        rec = self.db.query(FinancialRecommendation).filter(
            FinancialRecommendation.id == recommendation_id
        ).first()
        return self._build_recommendation_response(rec) if rec else None

    def record_merchant_interest(self, recommendation_id: str, notes: Optional[str] = None) -> FinancialRecommendationResponse:
        rec = self.db.query(FinancialRecommendation).filter(
            FinancialRecommendation.id == recommendation_id
        ).first()
        if not rec:
            raise ValueError(f"Financial recommendation '{recommendation_id}' not found.")

        rec.status = FinancialRecommendationStatus.INTERESTED
        rec.responded_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(rec)
        logger.info(f"Merchant {rec.merchant_id} expressed interest in recommendation {recommendation_id}")
        return self._build_recommendation_response(rec)

    def record_merchant_decline(self, recommendation_id: str, reason: Optional[str] = None) -> FinancialRecommendationResponse:
        rec = self.db.query(FinancialRecommendation).filter(
            FinancialRecommendation.id == recommendation_id
        ).first()
        if not rec:
            raise ValueError(f"Financial recommendation '{recommendation_id}' not found.")

        rec.status = FinancialRecommendationStatus.DECLINED
        rec.responded_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(rec)
        logger.info(f"Merchant {rec.merchant_id} declined recommendation {recommendation_id}")
        return self._build_recommendation_response(rec)

    def format_whatsapp_opportunity(self, rec: FinancialRecommendation) -> str:
        """
        Formats a merchant-friendly WhatsApp message highlighting the business opportunity.
        """
        lines = [
            "💡 *Paytm Pulse — Business Opportunity*",
            f"\n*{rec.title}*",
            f"\n{rec.reason}",
            "\n*Why you qualify:*",
        ]
        for sig in (rec.supporting_signals or []):
            lines.append(f"• {sig}")

        lines.extend([
            f"\n💰 *Pre-approved Limit:* ₹{float(rec.simulated_amount):,.2f}",
            f"⏱️ *Tenure:* {int(rec.duration_days)} days",
            "\nReply *VIEW DETAILS* or *NOT NOW* to proceed."
        ])
        return "\n".join(lines)

    def _build_recommendation_response(self, rec: FinancialRecommendation) -> FinancialRecommendationResponse:
        prod = rec.product
        return FinancialRecommendationResponse(
            id=rec.id,
            merchant_id=rec.merchant_id,
            product_id=rec.product_id,
            need_type=rec.need_type,
            title=rec.title,
            reason=rec.reason,
            supporting_signals=rec.supporting_signals or [],
            confidence=float(rec.confidence),
            simulated_amount=float(rec.simulated_amount),
            duration_days=int(rec.duration_days),
            status=rec.status.value if hasattr(rec.status, "value") else str(rec.status),
            product_name=prod.name if prod else None,
            product_category=prod.category if prod else None,
            interest_rate_display=prod.interest_rate_display if prod else "Simulated Demo Rate",
            disclaimer="Simulated product recommendation for demonstration purposes only.",
            created_at=rec.created_at,
            updated_at=rec.updated_at
        )
