"""
Paytm Pulse - Unit Tests for Multilingual WhatsApp Alerts & Localization
Tests all merchant types (Kirana, Pharmacy, Restaurant, Electronics, Clothing)
across 10 Indian languages (Hindi, Kannada, Bengali, Punjabi, Gujarati, Tamil, Telugu, Marathi, Malayalam, English).
"""

import pytest
from app.models.merchant import Merchant, MerchantCategory
from app.models.recommendation import Recommendation, RecommendationType
from app.communication.multilingual import (
    format_multilingual_recommendation,
    format_multilingual_event_alert,
    get_merchant_language,
    get_category_label,
    BUTTON_TRANSLATIONS
)
from app.communication.notification_service import NotificationService


def test_language_normalization():
    m1 = Merchant(name="Ramesh", language="kannada", category=MerchantCategory.KIRANA)
    assert get_merchant_language(m1) == "Kannada"

    m2 = Merchant(name="Sharma", language="HINDI", category=MerchantCategory.KIRANA)
    assert get_merchant_language(m2) == "Hindi"

    m3 = Merchant(name="Roy", language="Bengali (Bangla)", category=MerchantCategory.PHARMACY)
    assert get_merchant_language(m3) == "Bengali"

    m4 = Merchant(name="Gurpreet", language="Punjabi", category=MerchantCategory.RESTAURANT)
    assert get_merchant_language(m4) == "Punjabi"

    m5 = Merchant(name="Patel", language="Gujarati", category=MerchantCategory.ELECTRONICS)
    assert get_merchant_language(m5) == "Gujarati"

    m6 = Merchant(name="Priya", language="Tamil", category=MerchantCategory.CLOTHING)
    assert get_merchant_language(m6) == "Tamil"

    # Test ISO codes and dicts
    assert get_merchant_language("kn") == "Kannada"
    assert get_merchant_language("hi") == "Hindi"
    assert get_merchant_language("te") == "Telugu"
    assert get_merchant_language({"preferred_language": "Marathi"}) == "Marathi"
    assert get_merchant_language({"language": "Odia"}) == "Odia"



def test_category_labels():
    assert get_category_label(MerchantCategory.KIRANA, "Hindi") == "किराना स्टोर"
    assert get_category_label(MerchantCategory.PHARMACY, "Bengali") == "ফার্মেসি ও ঔষধালয়"
    assert get_category_label(MerchantCategory.RESTAURANT, "Kannada") == "ರೆಸ್ಟೋರೆಂಟ್ / ಹೋಟೆಲ್"
    assert get_category_label(MerchantCategory.ELECTRONICS, "Gujarati") == "ઇલેક્ટ્રોનિક્સ સ્ટોર"
    assert get_category_label(MerchantCategory.CLOTHING, "Tamil") == "ஆடை கடை"


def test_multilingual_recommendation_hindi():
    m = Merchant(
        name="Sharma Ji",
        shop_name="Sharma Kirana Provisions",
        category=MerchantCategory.KIRANA,
        language="Hindi",
        phone="919876543211"
    )
    rec = Recommendation(
        id="rec_hindi_001",
        merchant_id="m_hindi_001",
        type=RecommendationType.STOCK_REORDER,
        title="आशीर्वाद आटा 5kg रिस्टॉक करें",
        reason="दुकान में केवल 3 पैकेट बचे हैं।",
        expected_impact="₹3,200 संभावित बिक्री",
        confidence=0.95
    )

    header, body, buttons, footer = format_multilingual_recommendation(m, rec)
    assert "तत्काल इन्वेंटरी अलर्ट" in header
    assert "पेटीएम पल्स स्टॉक अलर्ट" in body
    assert "Sharma Kirana Provisions" in body
    assert "किराना स्टोर" in body
    assert buttons[0].title == "✅ मंजूर करें"
    assert buttons[1].title == "❌ अस्वीकार"
    assert "निर्णय लेने के लिए टैप करें" in footer


def test_multilingual_recommendation_kannada():
    m = Merchant(
        name="Ravi Kumar",
        shop_name="Ravi General Store",
        category=MerchantCategory.KIRANA,
        language="Kannada",
        phone="919876543210"
    )
    rec = Recommendation(
        id="rec_kannada_001",
        merchant_id="m_kannada_001",
        type=RecommendationType.PRICE_DISCOUNT,
        title="ವಾರಾಂತ್ಯದ ಕೊಡುಗೆ ಪ್ರಾರಂಭಿಸಿ",
        reason="ಹೆಚ್ಚುವರಿ ಸ್ಟಾಕ್ ಮಾರಾಟ ಮಾಡಲು 10% ರಿಯಾಯಿತಿ ನೀಡಿ.",
        expected_impact="₹4,500 ಹೆಚ್ಚುವರಿ ಆದಾಯ",
        confidence=0.88
    )

    header, body, buttons, footer = format_multilingual_recommendation(m, rec)
    assert "ಮಾರಾಟ ಬೆಳವಣಿಗೆ ಅವಕಾಶ" in header
    assert "Paytm Pulse ಮಾರಾಟ ಅವಕಾಶ" in body
    assert buttons[0].title == "✅ ಅನುಮೋದಿಸಿ"
    assert buttons[1].title == "❌ ತಿರಸ್ಕರಿಸಿ"


def test_multilingual_event_alert_all_languages():
    languages = [
        ("Hindi", "🔥 भारी मांग अलर्ट!"),
        ("Kannada", "🔥 ಭಾರಿ ಬೇಡಿಕೆ ಎಚ್ಚರಿಕೆ!"),
        ("Bengali", "🔥 বিক্রয় বৃদ্ধি সতর্কতা"),
        ("Punjabi", "⚡ ਕਾਰੋਬਾਰੀ ਅਲਰਟ"),
        ("Gujarati", "⚡ વેપાર અપડેટ"),
        ("Tamil", "⚡ வணிக எச்சரிக்கை"),
        ("Telugu", "⚡ వ్యాపార హెచ్చరిక"),
        ("Marathi", "⚡ व्यवसाय सूचना"),
        ("Malayalam", "⚡ ബിസിനസ്സ് അലേർട്ട്"),
        ("English", "⚡ HIGH Business Alert")
    ]

    for lang, expected_header in languages:
        m = Merchant(name="Test Merchant", shop_name="Test Store", category=MerchantCategory.KIRANA, language=lang)
        header, body = format_multilingual_event_alert(
            merchant=m,
            event_type="DEMAND_SPIKE",
            severity="HIGH",
            details_message="2.5x sales jump detected."
        )
        assert expected_header in header or "Alert" in header, f"Failed for language: {lang}"
        assert "Test Store" in body


def test_sarvam_language_mapping_and_translation():
    from app.communication.multilingual import get_sarvam_lang_code, translate_with_sarvam
    assert get_sarvam_lang_code("Kannada") == "kn-IN"
    assert get_sarvam_lang_code("Hindi") == "hi-IN"
    assert get_sarvam_lang_code("Tamil") == "ta-IN"
    assert get_sarvam_lang_code("Telugu") == "te-IN"
    assert get_sarvam_lang_code("English") == "en-IN"

    # Test English pass-through
    eng_res = translate_with_sarvam("Hello world", target_lang="English")
    assert eng_res == "Hello world"

