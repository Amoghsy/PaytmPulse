"""
Paytm Pulse - AI Daily Business Brief Service
Orchestrates collection of multi-horizon merchant telemetry, Gemini generative AI summarization,
deterministic fallback generation, PostgreSQL storage with idempotency, and WhatsApp/Dashboard distribution.
"""

import os
import json
import logging
import re
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from dotenv import load_dotenv

from app.models.merchant import Merchant
from app.models.business_brief import BusinessBrief, BriefGenerationSource
from app.models.business_event import BusinessEvent
from app.agent.tools.sales_tools import get_sales_analysis
from app.agent.tools.inventory_tools import get_all_stockout_risks
from app.agent.tools.customer_tools import get_customer_intelligence
from app.agent.tools.opportunity_tools import detect_opportunities
from app.agent.prompts import BRIEF_SYSTEM_INSTRUCTION, BRIEF_PROMPT_TEMPLATE
from app.communication.notification_service import NotificationService
from app.communication.multilingual import get_merchant_language
from app.services import redis_service

load_dotenv()
logger = logging.getLogger("paytm_pulse.services.brief")

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _get_current_date_str() -> str:
    """Returns today's date string in YYYY-MM-DD format (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def collect_merchant_brief_context(merchant_id: str, db: Session) -> Dict[str, Any]:
    """
    Consolidates real-time business telemetry for a merchant across sales, inventory,
    customer RFM segmentation, opportunities, and recent business events.
    """
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        raise ValueError(f"Merchant '{merchant_id}' not found")

    shop_name = merchant.shop_name or merchant.business_name or "Store"
    category = merchant.category.value if hasattr(merchant.category, "value") else str(merchant.category or "RETAIL")
    language = merchant.language or "English"

    # 1. Sales Analysis (Multi-horizon)
    try:
        sales_raw = get_sales_analysis(merchant_id, db=db)
    except Exception as e:
        logger.warning(f"Failed to fetch sales analysis for brief context: {e}")
        sales_raw = {}

    sales_summary = {
        "today_sales": float(sales_raw.get("today_sales", 0.0)),
        "yesterday_sales": float(sales_raw.get("yesterday_sales", 0.0)),
        "average_daily_sales": float(sales_raw.get("average_daily_sales", 0.0)),
        "last_30_days_sales": float(sales_raw.get("last_30_days_sales", 0.0)),
        "transaction_count": int(sales_raw.get("transaction_count", 0)),
        "growth_percentage": float(sales_raw.get("growth_percentage", 0.0)),
        "top_products": sales_raw.get("top_products", [])[:3],
    }

    # 2. Inventory & Stockout Risks
    try:
        stockouts_raw = get_all_stockout_risks(merchant_id, db=db)
        at_risk_list = stockouts_raw.get("at_risk_products", [])
    except Exception as e:
        logger.warning(f"Failed to fetch stockout risks for brief context: {e}")
        at_risk_list = []

    inventory_risks = []
    for item in at_risk_list[:5]:
        inventory_risks.append({
            "product_id": item.get("product_id"),
            "product_name": item.get("product_name"),
            "current_stock": item.get("current_stock", 0),
            "predicted_stockout_hours": item.get("predicted_stockout_hours"),
            "risk_level": item.get("risk_level", "MEDIUM"),
            "urgency": item.get("urgency", "HIGH")
        })

    # 3. Customer Intelligence (RFM)
    try:
        cust_raw = get_customer_intelligence(merchant_id, db=db)
    except Exception as e:
        logger.warning(f"Failed to fetch customer intelligence for brief context: {e}")
        cust_raw = {}

    segments_summary = cust_raw.get("segments_summary", {}) if isinstance(cust_raw.get("segments_summary"), dict) else {}

    def _extract_count(val, seg_name):
        if isinstance(val, list):
            return len(val)
        if isinstance(val, (int, float)):
            return int(val)
        return int(segments_summary.get(seg_name, 0) or 0)

    total_cust = cust_raw.get("total_customers", 0)
    if isinstance(total_cust, list):
        total_cust = len(total_cust)
    elif not isinstance(total_cust, (int, float)):
        total_cust = 0

    customer_summary = {
        "total_customers": int(total_cust),
        "active_customers": _extract_count(cust_raw.get("active_customers"), "ACTIVE"),
        "at_risk_customers": _extract_count(cust_raw.get("at_risk_customers"), "AT_RISK"),
        "inactive_customers": _extract_count(cust_raw.get("inactive_customers"), "INACTIVE"),
        "churn_risk_summary": cust_raw.get("churn_risk_summary", {}) if isinstance(cust_raw.get("churn_risk_summary"), dict) else {}
    }

    # 4. Detected Opportunities
    try:
        opps_raw = detect_opportunities(merchant_id, db=db)
        opportunities_list = opps_raw.get("opportunities", [])
    except Exception as e:
        logger.warning(f"Failed to fetch opportunities for brief context: {e}")
        opportunities_list = []

    opportunities = []
    for opp in opportunities_list[:4]:
        opportunities.append({
            "type": opp.get("opportunity_type") or opp.get("type", "GENERAL"),
            "title": opp.get("title", ""),
            "description": opp.get("description", ""),
            "expected_impact": opp.get("estimated_gain") or opp.get("expected_impact"),
            "urgency": opp.get("urgency", "MEDIUM")
        })

    # 5. Recent Meaningful Business Events (last 5)
    recent_events = []
    try:
        events = db.query(BusinessEvent)\
            .filter_by(merchant_id=merchant_id)\
            .order_by(desc(BusinessEvent.created_at))\
            .limit(5)\
            .all()
        for ev in events:
            recent_events.append({
                "event_id": ev.id,
                "event_type": ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type),
                "severity": ev.severity.value if hasattr(ev.severity, "value") else str(ev.severity),
                "title": ev.title,
                "created_at": ev.created_at.isoformat() if ev.created_at else None
            })
    except Exception as e:
        logger.warning(f"Failed to fetch recent events for brief context: {e}")

    return {
        "merchant": {
            "id": merchant.id,
            "name": merchant.name,
            "shop_name": shop_name,
            "category": category,
            "location": merchant.location,
            "language": language,
            "phone": merchant.phone
        },
        "sales": sales_summary,
        "inventory_risks": inventory_risks,
        "customer_intelligence": customer_summary,
        "opportunities": opportunities,
        "recent_events": recent_events,
        "collected_at": datetime.now(timezone.utc).isoformat()
    }


def _clean_json_str(text: str) -> Optional[Dict[str, Any]]:
    """Sanitizes markdown code fences and parses JSON securely."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return None


def _validate_brief_dict(data: Dict[str, Any]) -> bool:
    """Validates that structured brief contains essential non-empty fields."""
    if not isinstance(data, dict):
        return False
    if not data.get("headline") or not data.get("summary"):
        return False
    return True


def generate_deterministic_fallback_brief(context: Dict[str, Any], language: Optional[str] = "en") -> Dict[str, Any]:
    """
    Synthesizes a 100% grounded, high-quality business brief directly from live store telemetry.
    Ensures zero hallucination and reliable failover when Gemini API is unreachable.
    """
    merchant = context.get("merchant", {})
    shop_name = merchant.get("shop_name", "your store")
    sales = context.get("sales", {})
    inventory_risks = context.get("inventory_risks", [])
    cust_intel = context.get("customer_intelligence", {})
    opportunities = context.get("opportunities", [])

    today_sales = sales.get("today_sales", 0.0)
    avg_sales = sales.get("average_daily_sales", 0.0)
    growth_pct = sales.get("growth_percentage", 0.0)
    top_prods = sales.get("top_products", [])
    at_risk_count = len(inventory_risks)
    at_risk_raw = cust_intel.get("at_risk_customers", 0)
    at_risk_customers = len(at_risk_raw) if isinstance(at_risk_raw, list) else int(at_risk_raw or 0)

    # Determine trend
    if growth_pct > 2.0:
        sales_trend = "UP"
        growth_str = f"+{growth_pct:.1f}%"
    elif growth_pct < -2.0:
        sales_trend = "DOWN"
        growth_str = f"{growth_pct:.1f}%"
    else:
        sales_trend = "FLAT"
        growth_str = "Stable"

    # Multilingual headlines & summaries
    lang_code = (language or merchant.get("language") or "en").lower()
    is_kannada = "kn" in lang_code or "kannada" in lang_code
    is_hindi = "hi" in lang_code or "hindi" in lang_code

    if is_kannada:
        headline = f"ಶುಭೋದಯ! {shop_name} ನ ಇಂದಿನ ವ್ಯಾಪಾರ ಸ್ಥಿತಿ."
        summary = (
            f"ನಿಮ್ಮ ಅಂಗಡಿಯ ಸರಾಸರಿ ದಿನದ ವ್ಯಾಪಾರ ₹{avg_sales:,.2f} ಆಗಿದೆ. "
            f"{f'{at_risk_count} ಉತ್ಪನ್ನಗಳ ದಾಸ್ತಾನು ಕಡಿಮೆಯಾಗಿದೆ.' if at_risk_count > 0 else 'ದಾಸ್ತಾನು ಸ್ಥಿರವಾಗಿದೆ.'} "
            f"ಇಂದಿನ ಗರಿಷ್ಠ ಮಾರಾಟಕ್ಕೆ ಸಿದ್ಧರಾಗಿ."
        )
        closing = "ಪೇಟಿಎಂ ಪಲ್ಸ್ ನಿಮ್ಮ ಅಂಗಡಿಯ ಜೊತೆಗಿದೆ. ಇಂದಿನ ದಿನ ಶುಭವಾಗಲಿ!"
    elif is_hindi:
        headline = f"सुप्रभात! {shop_name} का आज का बिज़नेस अपडेट."
        summary = (
            f"आपकी दुकान की औसत दैनिक बिक्री ₹{avg_sales:,.2f} है। "
            f"{f'{at_risk_count} उत्पादों का स्टॉक खत्म होने का जोखिम है।' if at_risk_count > 0 else 'स्टॉक की स्थिति सामान्य है।'} "
            f"आज शाम की बिक्री बढ़ाने के लिए तैयार रहें।"
        )
        closing = "Paytm Pulse आपके व्यापार को बढ़ाने में सदैव तत्पर है।"
    else:
        headline = f"Good morning! Here is what needs your attention today at {shop_name}."
        if at_risk_count > 0:
            summary = f"Sales maintaining a baseline of ₹{avg_sales:,.2f}/day. {at_risk_count} item(s) need restocking before peak checkout."
        else:
            summary = f"Store performance is steady with an average daily sales baseline of ₹{avg_sales:,.2f}."
        closing = "Wishing you strong sales and smooth store operations today!"

    key_metrics = [
        {
            "label": "Avg Daily Sales",
            "value": f"₹{avg_sales:,.2f}",
            "trend": sales_trend,
            "change": growth_str
        },
        {
            "label": "Stockout Risks",
            "value": f"{at_risk_count} items",
            "trend": "DOWN" if at_risk_count > 0 else "FLAT",
            "change": "Urgent" if at_risk_count > 0 else "Normal"
        },
        {
            "label": "At-Risk Customers",
            "value": f"{at_risk_customers} customers",
            "trend": "DOWN" if at_risk_customers > 0 else "FLAT",
            "change": "Re-engage" if at_risk_customers > 0 else "Healthy"
        }
    ]

    important_insights = []
    if top_prods:
        top_p = top_prods[0]
        important_insights.append({
            "type": "SALES",
            "title": f"Top Performer: {top_p.get('product_name')}",
            "description": f"Generated ₹{top_p.get('revenue', 0.0):,.2f} from {top_p.get('units_sold', 0)} units.",
            "severity": "INFO"
        })

    attention_items = []
    for r in inventory_risks[:3]:
        p_name = r.get("product_name", "Product")
        stock = r.get("current_stock", 0)
        runway = r.get("predicted_stockout_hours")
        runway_text = f" (~{runway:.1f}h runway remaining)" if runway is not None else ""
        attention_items.append({
            "type": "STOCKOUT_RISK",
            "title": f"Low Stock: {p_name}",
            "description": f"Current stock: {stock} units{runway_text}. Restock advised before evening peak.",
            "urgency": r.get("urgency", "HIGH")
        })

    brief_opportunities = []
    for opp in opportunities[:3]:
        brief_opportunities.append({
            "type": opp.get("type", "PROMOTION"),
            "title": opp.get("title", "Growth Opportunity"),
            "description": opp.get("description", ""),
            "expected_impact": str(opp.get("expected_impact")) if opp.get("expected_impact") else None,
            "confidence": "HIGH"
        })

    recommended_actions = []
    if at_risk_count > 0:
        first_risk = inventory_risks[0]
        recommended_actions.append({
            "action_type": "RESTOCK_PRODUCT",
            "title": f"Reorder {first_risk.get('product_name')}",
            "reason": "Prevent lost checkout sales during evening peak footfall.",
            "requires_approval": True
        })
    elif opportunities:
        top_opp = opportunities[0]
        recommended_actions.append({
            "action_type": "LAUNCH_PROMOTION",
            "title": top_opp.get("title", "Launch Evening Combo Offer"),
            "reason": top_opp.get("description", "Drive incremental basket value."),
            "requires_approval": True
        })
    else:
        recommended_actions.append({
            "action_type": "MONITOR",
            "title": "Monitor Live Sales Velocity",
            "reason": "Store catalog inventory levels are currently optimal.",
            "requires_approval": False
        })

    return {
        "headline": headline,
        "summary": summary,
        "key_metrics": key_metrics,
        "important_insights": important_insights,
        "attention_items": attention_items,
        "opportunities": brief_opportunities,
        "recommended_actions": recommended_actions,
        "closing_message": closing
    }


def generate_brief_with_gemini(
    context: Dict[str, Any],
    language: Optional[str] = None
) -> Tuple[Dict[str, Any], str]:
    """
    Invokes Google Gemini model to generate a structured AI morning business brief.
    Gracefully falls back to deterministic synthesizer on API unavailability or schema violation.
    """
    merchant = context.get("merchant", {})
    shop_name = merchant.get("shop_name", "Store")
    category = merchant.get("category", "KIRANA")
    target_lang = language or merchant.get("language") or "English"

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        logger.info("No GOOGLE_API_KEY configured. Using deterministic fallback brief synthesizer.")
        return generate_deterministic_fallback_brief(context, language=target_lang), BriefGenerationSource.FALLBACK.value

    try:
        from google import genai
        from google.genai import types
        import concurrent.futures

        client = genai.Client(api_key=api_key)
        prompt_content = BRIEF_PROMPT_TEMPLATE.format(
            merchant_name=shop_name,
            merchant_category=category,
            target_language=target_lang,
            context_json=json.dumps(context, default=str, indent=2)
        )

        def _call_gemini():
            return client.models.generate_content(
                model=DEFAULT_MODEL,
                contents=[prompt_content],
                config=types.GenerateContentConfig(
                    system_instruction=BRIEF_SYSTEM_INSTRUCTION,
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_gemini)
            response = future.result(timeout=5.0)

        raw_text = getattr(response, "text", "") or ""
        parsed = _clean_json_str(raw_text)

        if parsed and _validate_brief_dict(parsed):
            logger.info(f"Gemini successfully synthesized daily brief for '{shop_name}' in {target_lang}")
            return parsed, BriefGenerationSource.GEMINI.value
        else:
            logger.warning(f"Gemini response failed validation. Falling back to deterministic brief.")
    except concurrent.futures.TimeoutError:
        logger.warning(f"Gemini call timed out (>5.0s) during daily brief generation. Instant failover to deterministic fallback.")
    except Exception as e:
        logger.warning(f"Gemini call error during daily brief generation: {e}. Falling back to deterministic.")

    return generate_deterministic_fallback_brief(context, language=target_lang), BriefGenerationSource.FALLBACK.value


def store_business_brief(
    merchant_id: str,
    brief_content: Dict[str, Any],
    brief_date: Optional[str] = None,
    generated_by: str = "gemini",
    language: str = "en",
    db: Optional[Session] = None
) -> BusinessBrief:
    """
    Persists business brief into PostgreSQL with daily idempotency (merchant_id + brief_date).
    Updates Redis caching layers for sub-millisecond retrieval.
    """
    if db is None:
        raise ValueError("Database session required to store business brief")

    date_str = brief_date or _get_current_date_str()
    headline = brief_content.get("headline", "Today's Business Brief")
    summary = brief_content.get("summary", "Your store overview is ready.")

    existing = db.query(BusinessBrief)\
        .filter_by(merchant_id=merchant_id, brief_date=date_str)\
        .first()

    if existing:
        existing.headline = headline
        existing.summary = summary
        existing.content = brief_content
        existing.generated_by = generated_by
        existing.language = language
        existing.updated_at = datetime.now(timezone.utc)
        record = existing
    else:
        record = BusinessBrief(
            merchant_id=merchant_id,
            brief_date=date_str,
            headline=headline,
            summary=summary,
            content=brief_content,
            generated_by=generated_by,
            language=language,
            dashboard_delivered=True,
            whatsapp_delivered=False
        )
        db.add(record)

    db.commit()
    db.refresh(record)

    # Update Redis cache
    try:
        cache_data = {
            "id": record.id,
            "merchant_id": record.merchant_id,
            "brief_date": record.brief_date,
            "headline": record.headline,
            "summary": record.summary,
            "content": record.content,
            "generated_by": record.generated_by,
            "language": record.language,
            "dashboard_delivered": record.dashboard_delivered,
            "whatsapp_delivered": record.whatsapp_delivered,
            "created_at": record.created_at.isoformat() if record.created_at else None
        }
        redis_service.set_key(f"merchant:{merchant_id}:brief:{date_str}", json.dumps(cache_data), expire_seconds=86400)
        redis_service.set_key(f"merchant:{merchant_id}:brief:latest", json.dumps(cache_data), expire_seconds=86400)
    except Exception as e:
        logger.debug(f"Redis cache set failed for brief: {e}")

    logger.info(f"Stored daily business brief for merchant '{merchant_id}' on {date_str} (source: {generated_by})")
    return record


def get_latest_brief(merchant_id: str, db: Session) -> Optional[BusinessBrief]:
    """Retrieves latest generated business brief for a merchant."""
    # Try fast Redis lookup
    try:
        cached = redis_service.get_key(f"merchant:{merchant_id}:brief:latest")
        if cached:
            parsed = json.loads(cached)
            # Reconstruct or verify DB record
            record = db.query(BusinessBrief).filter_by(id=parsed.get("id")).first()
            if record:
                return record
    except Exception:
        pass

    return db.query(BusinessBrief)\
        .filter_by(merchant_id=merchant_id)\
        .order_by(desc(BusinessBrief.brief_date), desc(BusinessBrief.created_at))\
        .first()


def format_whatsapp_brief_message(brief: BusinessBrief, merchant: Merchant) -> str:
    """Formats a concise, merchant-friendly WhatsApp text message from the structured brief."""
    content = brief.content or {}
    shop_name = merchant.shop_name or merchant.business_name or "Store"
    lang = (brief.language or merchant.language or "en").lower()

    is_kannada = "kn" in lang or "kannada" in lang
    is_hindi = "hi" in lang or "hindi" in lang

    key_metrics = content.get("key_metrics", [])
    attention_items = content.get("attention_items", [])
    opportunities = content.get("opportunities", [])
    recommended_actions = content.get("recommended_actions", [])

    # Extract highlights
    sales_metric = next((m for m in key_metrics if "sales" in m.get("label", "").lower()), None)
    sales_text = f"{sales_metric.get('value')} ({sales_metric.get('change')})" if sales_metric else "Active"
    
    attention_count = len(attention_items)
    top_opp = opportunities[0] if opportunities else None
    top_act = recommended_actions[0] if recommended_actions else None

    if is_kannada:
        msg = f"🌅 *ಪೇಟಿಎಂ ಪಲ್ಸ್ — ಇಂದಿನ ಮುಂಜಾನೆ ವರದಿ*\n_{shop_name}_\n\n"
        msg += f"📈 *ವ್ಯಾಪಾರ:* {sales_text}\n"
        if attention_count > 0:
            msg += f"⚠️ *ಗಮನಿಸಿ:* {attention_count} ಉತ್ಪನ್ನಗಳ ದಾಸ್ತಾನು ಕಡಿಮೆಯಾಗಿದೆ.\n"
        if top_opp:
            msg += f"💡 *ಅವಕಾಶ:* {top_opp.get('title')}\n"
        if top_act:
            msg += f"🎯 *ಶಿಫಾರಸು:* {top_act.get('title')}\n\n"
        msg += "👉 ಹೆಚ್ಚಿನ ವಿವರಗಳಿಗೆ ಪೇಟಿಎಂ ಪಲ್ಸ್ ಆ್ಯಪ್ ತೆರೆಯಿರಿ."
    elif is_hindi:
        msg = f"🌅 *Paytm Pulse — आज का मॉर्निंग ब्रीफ*\n_{shop_name}_\n\n"
        msg += f"📈 *बिक्री:* {sales_text}\n"
        if attention_count > 0:
            msg += f"⚠️ *ध्यान दें:* {attention_count} उत्पादों का स्टॉक कम है।\n"
        if top_opp:
            msg += f"💡 *अवसर:* {top_opp.get('title')}\n"
        if top_act:
            msg += f"🎯 *सुझाव:* {top_act.get('title')}\n\n"
        msg += "👉 विवरण के लिए Paytm Pulse ऐप खोलें।"
    else:
        msg = f"🌅 *Paytm Pulse — Morning Business Brief*\n_{shop_name}_\n\n"
        msg += f"📈 *Sales:* {sales_text}\n"
        if attention_count > 0:
            msg += f"⚠️ *Attention:* {attention_count} product(s) require replenishment.\n"
        if top_opp:
            msg += f"💡 *Opportunity:* {top_opp.get('title')}\n"
        if top_act:
            msg += f"🎯 *Recommended:* {top_act.get('title')}\n\n"
        msg += "👉 Open Paytm Pulse for complete details."

    return msg


def send_brief_whatsapp_notification(
    merchant_id: str,
    brief: BusinessBrief,
    db: Session,
    custom_message: Optional[str] = None
) -> Dict[str, Any]:
    """Dispatches concise morning business brief over WhatsApp (with mock support)."""
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        raise ValueError(f"Merchant '{merchant_id}' not found")

    message_text = custom_message or format_whatsapp_brief_message(brief, merchant)
    notification_svc = NotificationService(db=db)

    from app.whatsapp.client import whatsapp_client
    res = whatsapp_client.send_text_message(
        recipient_phone=merchant.phone,
        text=message_text
    )

    brief.whatsapp_delivered = True
    db.commit()

    return {
        "status": "sent" if "error" not in res else "failed",
        "merchant_id": merchant_id,
        "brief_id": brief.id,
        "whatsapp_response": res,
        "message_text": message_text
    }
