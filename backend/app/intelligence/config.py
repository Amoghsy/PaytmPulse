import os
from dotenv import load_dotenv

load_dotenv()

# Data limits & thresholds
MIN_HISTORY_DAYS = int(os.getenv("ML_MIN_HISTORY_DAYS", 7))
FORECAST_HORIZON_HOURS = int(os.getenv("ML_FORECAST_HORIZON_HOURS", 24))

# Stockout hours thresholds
STOCKOUT_CRITICAL_HOURS = float(os.getenv("STOCKOUT_CRITICAL_HOURS", 2.0))
STOCKOUT_HIGH_HOURS = float(os.getenv("STOCKOUT_HIGH_HOURS", 6.0))
STOCKOUT_MEDIUM_HOURS = float(os.getenv("STOCKOUT_MEDIUM_HOURS", 24.0))

# Customer intelligence thresholds
CUSTOMER_INACTIVE_DAYS = int(os.getenv("CUSTOMER_INACTIVE_DAYS", 14))
CUSTOMER_AT_RISK_DAYS = int(os.getenv("CUSTOMER_AT_RISK_DAYS", 30))
CUSTOMER_HIGH_VALUE_THRESHOLD = float(os.getenv("CUSTOMER_HIGH_VALUE_THRESHOLD", 2000.0))

# Anomaly detection contamination & threshold
ANOMALY_CONTAMINATION = float(os.getenv("ANOMALY_CONTAMINATION", 0.05))
ANOMALY_SPIKE_RATIO = float(os.getenv("ANOMALY_SPIKE_RATIO", 1.8))

# Model persistence & directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(BASE_DIR, "ml_models")
ANOMALY_MODELS_DIR = os.path.join(MODELS_DIR, "anomaly")
DEMAND_MODELS_DIR = os.path.join(MODELS_DIR, "demand")

# Redis caching TTL
CACHE_TTL_SECONDS = int(os.getenv("INTELLIGENCE_CACHE_TTL", 300))
