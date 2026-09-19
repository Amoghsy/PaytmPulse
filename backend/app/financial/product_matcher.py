import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.financial_product import FinancialProduct
from app.financial.schemas import FinancialNeedDetectionResult, FinancialNeedType

logger = logging.getLogger("paytm_pulse.financial.product_matcher")


class ProductMatcher:
    """
    Matches detected business financial needs to appropriate simulated products
    and bounds simulated demo amounts safely.
    """

    def __init__(self, db: Session):
        self.db = db

    def match_product(self, need: FinancialNeedDetectionResult) -> Tuple[Optional[FinancialProduct], float, int, str]:
        """
        Finds the matching simulated product in the catalog.
        Returns (product, simulated_amount, duration_days, title).
        """
        if not need.need_detected or not need.need_type:
            return None, 0.0, 0, ""

        category_name = need.need_type.value if hasattr(need.need_type, "value") else str(need.need_type)
        product = self.db.query(FinancialProduct).filter(
            FinancialProduct.category == category_name,
            FinancialProduct.active == True
        ).first()

        if not product:
            logger.warning(f"No active financial product found for category '{category_name}'")
            return None, 0.0, 0, ""

        # Safe bounding against product max limit
        max_limit = float(product.max_simulated_amount)
        calculated_amt = need.estimated_requirement_amount if need.estimated_requirement_amount > 0 else (max_limit * 0.5)
        simulated_amt = round(min(max_limit, max(5000.0, calculated_amt)), -2)
        duration = product.duration_days

        title_map = {
            FinancialNeedType.WORKING_CAPITAL: "Potential Working Capital Support",
            FinancialNeedType.INVENTORY_FINANCING: "Inventory Financing Opportunity",
            FinancialNeedType.BUSINESS_EXPANSION: "Business Expansion Facility",
            FinancialNeedType.CASH_FLOW_SUPPORT: "Short-Term Cash Flow Support",
        }
        title = title_map.get(need.need_type, f"Simulated {product.name}")

        return product, simulated_amt, duration, title
