import os

# Configurable TTLs (in seconds)
REDIS_RECENT_TRANSACTION_TTL = int(os.getenv("REDIS_RECENT_TRANSACTION_TTL", 3600))        # 1 hour
REDIS_MAX_RECENT_TRANSACTIONS = int(os.getenv("REDIS_MAX_RECENT_TRANSACTIONS", 50))       # Top 50 items
REDIS_ALERT_TTL = int(os.getenv("REDIS_ALERT_TTL", 86400))                                 # 24 hours
REDIS_SESSION_TTL = int(os.getenv("REDIS_SESSION_TTL", 1800))                              # 30 minutes
REDIS_CONVERSATION_TTL = int(os.getenv("REDIS_CONVERSATION_TTL", 3600))                    # 1 hour
REDIS_MAX_CONVERSATION_MESSAGES = int(os.getenv("REDIS_MAX_CONVERSATION_MESSAGES", 20))   # Top 20 turns
REDIS_RECOMMENDATION_TTL = int(os.getenv("REDIS_RECOMMENDATION_TTL", 3600))                # 1 hour
REDIS_AGENT_CONTEXT_TTL = int(os.getenv("REDIS_AGENT_CONTEXT_TTL", 1800))                  # 30 minutes
REDIS_INTELLIGENCE_CACHE_TTL = int(os.getenv("REDIS_INTELLIGENCE_CACHE_TTL", 300))         # 5 minutes
REDIS_FINANCIAL_COOLDOWN_TTL = int(os.getenv("REDIS_FINANCIAL_COOLDOWN_TTL", 604800))      # 7 days
