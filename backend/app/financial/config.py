import os

# Configurable Signal Thresholds
DEMAND_GROWTH_THRESHOLD = float(os.getenv("DEMAND_GROWTH_THRESHOLD", 0.25))  # 25% demand surge
RESTOCK_FREQUENCY_THRESHOLD = int(os.getenv("RESTOCK_FREQUENCY_THRESHOLD", 2))  # >= 2 reorders in 7 days
SALES_GROWTH_THRESHOLD = float(os.getenv("SALES_GROWTH_THRESHOLD", 0.15))  # 15% sales growth
CUSTOMER_GROWTH_THRESHOLD = float(os.getenv("CUSTOMER_GROWTH_THRESHOLD", 0.10))  # 10% active customer growth
FINANCIAL_RECOMMENDATION_COOLDOWN_DAYS = int(os.getenv("FINANCIAL_RECOMMENDATION_COOLDOWN_DAYS", 7))

# Standard Simulated Catalog Definitions
SIMULATED_FINANCIAL_PRODUCTS = [
    {
        "product_code": "WORKING_CAPITAL_SIM",
        "name": "Working Capital Support",
        "category": "WORKING_CAPITAL",
        "description": "Simulated short-term working capital support to manage rapid inventory demand surges and supplier payables for demo purposes.",
        "min_signal_confidence": 0.75,
        "max_simulated_amount": 50000.0,
        "duration_days": 90,
        "interest_rate_display": "Simulated Demo Rate",
        "simulated": True,
        "active": True
    },
    {
        "product_code": "INVENTORY_FINANCING_SIM",
        "name": "Inventory Financing",
        "category": "INVENTORY_FINANCING",
        "description": "Simulated revolving credit line designed for frequent inventory replenishment of fast-moving SKU categories.",
        "min_signal_confidence": 0.70,
        "max_simulated_amount": 75000.0,
        "duration_days": 60,
        "interest_rate_display": "Simulated Demo Rate",
        "simulated": True,
        "active": True
    },
    {
        "product_code": "BUSINESS_EXPANSION_SIM",
        "name": "Business Expansion Support",
        "category": "BUSINESS_EXPANSION",
        "description": "Simulated expansion facility to support store scale-up, catalog extension, or infrastructure upgrade following sustained growth.",
        "min_signal_confidence": 0.80,
        "max_simulated_amount": 150000.0,
        "duration_days": 180,
        "interest_rate_display": "Simulated Demo Rate",
        "simulated": True,
        "active": True
    },
    {
        "product_code": "CASH_FLOW_SUPPORT_SIM",
        "name": "Cash Flow Support",
        "category": "CASH_FLOW_SUPPORT",
        "description": "Simulated short-term buffer to assist merchants managing temporary timing mismatches between inventory commitments and sales collections.",
        "min_signal_confidence": 0.70,
        "max_simulated_amount": 35000.0,
        "duration_days": 45,
        "interest_rate_display": "Simulated Demo Rate",
        "simulated": True,
        "active": True
    }
]
