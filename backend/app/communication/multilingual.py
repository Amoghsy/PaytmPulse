"""
Paytm Pulse - Multilingual Alert Translation & Localization Engine powered strictly by Sarvam AI
Formats proactive business alerts and recommendations dynamically in the merchant's exact preferred language
using Sarvam AI Mayura Translation API exclusively.
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple, List
from app.models.merchant import Merchant, MerchantCategory
from app.models.business_event import BusinessEvent, EventType, EventSeverity
from app.models.recommendation import Recommendation, RecommendationType
from app.whatsapp.schemas import WhatsAppQuickReplyButton
from app.voice.sarvam_client import sarvam_client

logger = logging.getLogger("paytm_pulse.communication.multilingual")

# Comprehensive mapping of all Indian language names, ISO codes, and aliases to Sarvam AI language codes
SARVAM_LANG_MAP: Dict[str, str] = {
    "Hindi": "hi-IN",
    "Kannada": "kn-IN",
    "Bengali": "bn-IN",
    "Punjabi": "pa-IN",
    "Gujarati": "gu-IN",
    "Tamil": "ta-IN",
    "Telugu": "te-IN",
    "Marathi": "mr-IN",
    "Malayalam": "ml-IN",
    "Odia": "od-IN",
    "Assamese": "as-IN",
    "Urdu": "ur-IN",
    "English": "en-IN",
    # Aliases and ISO codes
    "hi": "hi-IN",
    "kn": "kn-IN",
    "bn": "bn-IN",
    "pa": "pa-IN",
    "gu": "gu-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "mr": "mr-IN",
    "ml": "ml-IN",
    "od": "od-IN",
    "as": "as-IN",
    "ur": "ur-IN",
    "en": "en-IN",
    "bangla": "bn-IN",
    "oriya": "od-IN",
    "asamiya": "as-IN"
}

# Standard button labels translated dynamically or mapped
BUTTON_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "Hindi": {
        "approve": "✅ मंजूर करें",
        "reject": "❌ अस्वीकार",
        "details": "ℹ️ विवरण",
        "footer": "पेटीएम पल्स • निर्णय लेने के लिए टैप करें"
    },
    "Kannada": {
        "approve": "✅ ಅನುಮೋದಿಸಿ",
        "reject": "❌ ತಿರಸ್ಕರಿಸಿ",
        "details": "ℹ️ ವಿವರಗಳು",
        "footer": "Paytm Pulse • ನಿರ್ಧರಿಸಲು ಟ್ಯಾಪ್ ಮಾಡಿ"
    },
    "Bengali": {
        "approve": "✅ অনুমোদন করুন",
        "reject": "❌ বাতিল করুন",
        "details": "ℹ️ বিস্তারিত",
        "footer": "Paytm Pulse • সিদ্ধান্ত নিতে ট্যাপ করুন"
    },
    "Punjabi": {
        "approve": "✅ ਮਨਜ਼ੂਰ ਕਰੋ",
        "reject": "❌ ਰੱਦ ਕਰੋ",
        "details": "ℹ️ ਵੇਰਵਾ",
        "footer": "Paytm Pulse • ਫੈਸਲਾ ਲੈਣ ਲਈ ਟੈਪ ਕਰੋ"
    },
    "Gujarati": {
        "approve": "✅ મંજૂર કરો",
        "reject": "❌ નકારો",
        "details": "ℹ️ વિગતો",
        "footer": "Paytm Pulse • નિર્ણય લેવા માટે ટૅપ કરો"
    },
    "Tamil": {
        "approve": "✅ ஒப்புதல்",
        "reject": "❌ நிராகரி",
        "details": "ℹ️ விவரங்கள்",
        "footer": "Paytm Pulse • தீர்மானிக்க தட்டவும்"
    },
    "Telugu": {
        "approve": "✅ ఆమోదించండి",
        "reject": "❌ తిరస్కరించండి",
        "details": "ℹ️ వివరాలు",
        "footer": "Paytm Pulse • నిర్ణయించడానికి నొక్కండి"
    },
    "Marathi": {
        "approve": "✅ मंजूर करा",
        "reject": "❌ नाकारा",
        "details": "ℹ️ तपशील",
        "footer": "Paytm Pulse • निर्णय घेण्यासाठी टॅप करा"
    },
    "Malayalam": {
        "approve": "✅ അംഗീകരിക്കുക",
        "reject": "❌ നിരസിക്കുക",
        "details": "ℹ️ വിശദാംശങ്ങൾ",
        "footer": "Paytm Pulse • തീരുമാനിക്കാൻ ടാപ്പ് ചെയ്യുക"
    },
    "Odia": {
        "approve": "✅ ଅନୁମୋଦନ କରନ୍ତୁ",
        "reject": "❌ ପ୍ରତ୍ୟାଖ୍ୟାନ",
        "details": "ℹ️ ବିବରଣୀ",
        "footer": "Paytm Pulse • ନିଷ୍ପତ୍ତି ନେବାକୁ ଟ୍ୟାପ୍ କରନ୍ତୁ"
    },
    "Assamese": {
        "approve": "✅ অনুমোদন কৰক",
        "reject": "❌ নাকচ কৰক",
        "details": "ℹ️ বিৱৰণ",
        "footer": "Paytm Pulse • সিদ্ধান্ত লবলৈ টেপ কৰক"
    },
    "English": {
        "approve": "✅ Approve",
        "reject": "❌ Reject",
        "details": "ℹ️ Details",
        "footer": "Paytm Pulse • Tap or Reply to Decide"
    }
}


def get_merchant_language(merchant: Any) -> str:
    """Normalizes merchant language to supported language name across all formats."""
    if isinstance(merchant, str):
        raw_lang = merchant
    elif isinstance(merchant, dict):
        raw_lang = merchant.get("preferred_language") or merchant.get("language") or "Hindi"
    elif merchant is not None:
        raw_lang = (
            getattr(merchant, "preferred_language", None)
            or getattr(merchant, "language", None)
            or "Hindi"
        )
    else:
        raw_lang = "Hindi"
    clean = str(raw_lang).strip()

    # Exact match in button translations
    for name in BUTTON_TRANSLATIONS.keys():
        if clean.lower() == name.lower():
            return name

    # Alias / code lookup
    if clean.lower() in SARVAM_LANG_MAP:
        target_code = SARVAM_LANG_MAP[clean.lower()]
        for name, code in SARVAM_LANG_MAP.items():
            if code == target_code and name in BUTTON_TRANSLATIONS:
                return name

    # Substring matching (e.g. "Bengali (Bangla)" -> "Bengali")
    for supported in BUTTON_TRANSLATIONS.keys():
        if supported.lower() in clean.lower():
            return supported

    for key, code in SARVAM_LANG_MAP.items():
        if key.lower() in clean.lower():
            for name, scode in SARVAM_LANG_MAP.items():
                if scode == code and name in BUTTON_TRANSLATIONS:
                    return name

    return clean.capitalize() if clean else "English"


def get_sarvam_lang_code(lang_name: str) -> str:
    """Returns Sarvam AI language code (e.g. kn-IN, hi-IN, ta-IN, bn-IN, mr-IN, etc.)."""
    clean_name = str(lang_name).strip()
    if clean_name.lower() in SARVAM_LANG_MAP:
        return SARVAM_LANG_MAP[clean_name.lower()]
    clean_cap = clean_name.capitalize()
    if clean_cap in SARVAM_LANG_MAP:
        return SARVAM_LANG_MAP[clean_cap]
    for key, code in SARVAM_LANG_MAP.items():
        if key.lower() in clean_name.lower():
            return code
    return "en-IN"


def translate_with_sarvam(
    text: str,
    target_lang: str,
    source_lang: str = "English",
    mode: str = "formal"
) -> str:
    """
    Translates text directly using Sarvam AI Mayura Translation API.
    """
    target_code = get_sarvam_lang_code(target_lang)
    source_code = get_sarvam_lang_code(source_lang)

    if not text or target_code == source_code or target_code == "en-IN":
        return text

    res = sarvam_client.translate(
        input_text=text,
        target_language_code=target_code,
        source_language_code=source_code,
        mode=mode
    )
    return res.get("translated_text", text)


def get_category_label(category: Any) -> str:
    """Returns category name in standard English."""
    cat_str = category.value if hasattr(category, "value") else str(category).upper()
    cat_map = {
        "KIRANA": "Kirana & Grocery Store",
        "PHARMACY": "Pharmacy & Healthcare",
        "RESTAURANT": "Restaurant & Dining",
        "ELECTRONICS": "Electronics & Mobiles",
        "CLOTHING": "Clothing & Apparel"
    }
    return cat_map.get(cat_str, "Retail Store")


def format_multilingual_recommendation(
    merchant: Merchant,
    recommendation: Recommendation
) -> Tuple[str, str, List[WhatsAppQuickReplyButton], str]:
    """
    Translates Next Best Action recommendation into merchant's native tongue using Sarvam AI Mayura Translation.
    Returns: (header_text, body_text, buttons, footer_text)
    """
    lang = get_merchant_language(merchant)
    target_code = get_sarvam_lang_code(lang)
    btn_dict = BUTTON_TRANSLATIONS.get(lang, BUTTON_TRANSLATIONS["English"])

    rec_type_val = recommendation.type.value if hasattr(recommendation.type, "value") else str(recommendation.type)
    title = getattr(recommendation, "title", "Next Best Action")
    clean_title = title.replace(": None", "").replace(": null", "").strip()
    reason = getattr(recommendation, "reason", "Recommended based on live store metrics.")
    
    # Impact extraction
    est_impact = 2500.0
    impact_raw = getattr(recommendation, "expected_impact", None)
    if impact_raw is not None:
        if isinstance(impact_raw, (int, float)):
            est_impact = float(impact_raw)
        elif isinstance(impact_raw, dict):
            try:
                est_impact = float(impact_raw.get("value", 2500.0))
            except Exception:
                est_impact = 2500.0
        else:
            match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)', str(impact_raw))
            if match:
                clean_num = match.group(1).replace(",", "")
                try:
                    est_impact = float(clean_num)
                except Exception:
                    est_impact = 2500.0

    shop = merchant.shop_name or "Store"
    cat_label = get_category_label(merchant.category)

    # 1. Base English Prompt
    if "STOCK" in rec_type_val or "RESTOCK" in rec_type_val:
        base_header = "🚨 Urgent Stock Restock Alert"
        base_body = (
            f"⚠️ Paytm Pulse Stock Alert • {shop} ({cat_label})\n\n"
            f"Action: {clean_title}\n"
            f"Reason: {reason}\n\n"
            f"Estimated Potential Gain: Rs. {est_impact:,.2f}\n\n"
            f"Would you like to approve and execute this order?"
        )
    elif "PROMOTION" in rec_type_val or "GROWTH" in rec_type_val or "BUNDLE" in rec_type_val:
        base_header = "✨ Revenue Growth & Combo Opportunity"
        base_body = (
            f"📈 Paytm Pulse Sales Opportunity • {shop} ({cat_label})\n\n"
            f"Action: {clean_title}\n"
            f"Details: {reason}\n\n"
            f"Projected Additional Revenue: Rs. {est_impact:,.2f}\n\n"
            f"Would you like to activate this promotion?"
        )
    elif "CUSTOMER" in rec_type_val or "WINBACK" in rec_type_val:
        base_header = "👥 Customer Retention Campaign"
        base_body = (
            f"👥 Paytm Pulse Customer Intelligence • {shop} ({cat_label})\n\n"
            f"Action: {clean_title}\n"
            f"Strategy: {reason}\n\n"
            f"Projected Revenue Recovery: Rs. {est_impact:,.2f}\n\n"
            f"Would you like to send this offer to customers?"
        )
    else:
        base_header = "⚡ Next Best Action Recommendation"
        base_body = (
            f"💡 Paytm Pulse AI Recommendation • {shop} ({cat_label})\n\n"
            f"Action: {clean_title}\n"
            f"Rationale: {reason}\n\n"
            f"Estimated Value Impact: Rs. {est_impact:,.2f}\n\n"
            f"Would you like to approve and execute this recommendation?"
        )

    # 2. Translate dynamically via Sarvam AI
    if target_code != "en-IN":
        logger.info(f"Translating recommendation alert to {target_code} using Sarvam AI Mayura Translation...")
        tr_header = sarvam_client.translate(base_header, target_language_code=target_code)
        tr_body = sarvam_client.translate(base_body, target_language_code=target_code)
        header = tr_header.get("translated_text", base_header)
        body = tr_body.get("translated_text", base_body)
    else:
        header = base_header
        body = base_body

    buttons = [
        WhatsAppQuickReplyButton(id=f"APPROVE_{recommendation.id}", title=btn_dict["approve"]),
        WhatsAppQuickReplyButton(id=f"REJECT_{recommendation.id}", title=btn_dict["reject"]),
        WhatsAppQuickReplyButton(id=f"DETAILS_{recommendation.id}", title=btn_dict["details"])
    ]

    return header, body, buttons, btn_dict["footer"]


def format_multilingual_event_alert(
    merchant: Merchant,
    event_type: str,
    severity: str,
    details_message: str
) -> Tuple[str, str]:
    """
    Formats a real-time business telemetry alert into the merchant's preferred language using Sarvam AI Translation.
    Returns: (header_text, body_text)
    """
    lang = get_merchant_language(merchant)
    shop = merchant.shop_name or "Store"
    cat_label = get_category_label(merchant.category)
    target_code = get_sarvam_lang_code(lang)

    base_header = f"⚡ {severity} Priority Business Alert"
    base_body = f"Paytm Pulse Alert • {shop} ({cat_label})\n\nEvent: {event_type.replace('_', ' ')}\nDetails: {details_message}"

    if target_code != "en-IN":
        logger.info(f"Translating event alert to {target_code} using Sarvam AI Mayura Translation...")
        tr_header = sarvam_client.translate(base_header, target_language_code=target_code)
        tr_body = sarvam_client.translate(base_body, target_language_code=target_code)
        header = tr_header.get("translated_text", base_header)
        body = tr_body.get("translated_text", base_body)
    else:
        header = base_header
        body = base_body

    return header, body
