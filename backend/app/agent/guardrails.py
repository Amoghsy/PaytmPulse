"""
Paytm Pulse - Phase 5 AI Guardrails
Enforces strict domain boundaries, prevents prompt injections/jailbreaks,
and filters out non-business inquiries (coding, trivia, politics, medical/legal, entertainment)
with native multilingual refusal responses.
"""

import re
import logging
from typing import Tuple, Dict, Optional

logger = logging.getLogger("paytm_pulse.guardrails")

# ---------------------------------------------------------------------------
# Multilingual Polite Refusal Templates
# ---------------------------------------------------------------------------
REFUSAL_MESSAGES: Dict[str, str] = {
    "en": (
        "I am **Paytm Pulse**, your dedicated AI Store Business Partner. "
        "I can only assist with your store's sales, inventory, revenue, customer insights, and business recommendations. "
        "Please ask me anything regarding your shop operations!"
    ),
    "hi": (
        "मैं **Paytm Pulse** हूँ, आपकी दुकान का AI बिज़नेस पार्टनर। "
        "मैं केवल आपकी दुकान की बिक्री, इन्वेंट्री, मुनाफ़े, ग्राहकों और व्यापार से जुड़े सवालों में आपकी मदद कर सकता हूँ। "
        "कृपया अपने स्टोर संचालन से संबंधित कोई भी सवाल पूछें!"
    ),
    "kn": (
        "ನಾನು **Paytm Pulse**, ನಿಮ್ಮ ಅಂಗಡಿಯ AI ವ್ಯಾಪಾರ ಪಾಲುದಾರ (Business Partner). "
        "ನಾನು ಕೇವಲ ನಿಮ್ಮ ಅಂಗಡಿಯ ಮಾರಾಟ, ದಾಸ್ತಾನು (Inventory), ಆದಾಯ ಮತ್ತು ವ್ಯಾಪಾರದ ಶಿಫಾರಸುಗಳ ಬಗ್ಗೆ ಮಾತ್ರ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ. "
        "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಅಂಗಡಿ ಕಾರ್ಯಾಚರಣೆಗೆ ಸಂಬಂಧಿಸಿದ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ!"
    ),
    "ta": (
        "நான் **Paytm Pulse**, உங்கள் கடையின் AI வணிக கூட்டாளி. "
        "உங்கள் கடையின் விற்பனை, இருப்பு (Inventory), வருவாய் மற்றும் வணிகம் தொடர்பான கேள்விகளுக்கு மட்டுமே என்னால் பதிலளிக்க முடியும். "
        "உங்கள் கடை தொடர்பான கேள்விகளைக் கேளுங்கள்!"
    ),
    "te": (
        "నేను **Paytm Pulse**, మీ దుకాణం AI వ్యాపార భాగస్వామిని. "
        "నేను మీ స్టోర్ అమ్మకాలు, ఇన్వెంటరీ, రాబడి మరియు వ్యాపార సిఫార్సులకు సంబంధించిన ప్రశ్నలకు మాత్రమే సహాయం చేయగలను. "
        "దయచేసి మీ దుకాణం గురించిన ప్రశ్నలు అడగండి!"
    ),
    "mr": (
        "मी **Paytm Pulse** आहे, तुमच्या दुकानाचा AI बिझनेस पार्टनर. "
        "मी फक्त तुमच्या दुकानाची विक्री, इन्व्हेंटरी, नफा आणि व्यवसायाशी संबंधित प्रश्नांमध्ये मदत करू शकतो. "
        "कृपया तुमच्या दुकानाच्या कामकाजाविषयी विचारा!"
    ),
    "gu": (
        "હું **Paytm Pulse** છું, તમારી દુકાનનો AI બિઝનેસ પાર્ટનર. "
        "હું ફક્ત તમારી દુકાનના વેચાણ, સ્ટોક (Inventory), નફો અને વ્યવસાય સંબંધિત પ્રશ્નોમાં જ મદદ કરી શકું છું. "
        "કૃપા કરીને તમારી દુકાનની કામગીરી સંબંધિત પ્રશ્નો પૂછો!"
    ),
    "bn": (
        "আমি **Paytm Pulse**, আপনার দোকানের AI ব্যবসায়িক অংশীদার। "
        "আমি শুধুমাত্র আপনার দোকানের বিক্রি, স্টক (Inventory), আয় এবং ব্যবসার সাথে সম্পর্কিত প্রশ্নে সাহায্য করতে পারি। "
        "দয়া করে আপনার দোকানের কাজকর্ম সংক্রান্ত প্রশ্ন জিজ্ঞাসা করুন!"
    )
}

# ---------------------------------------------------------------------------
# Allowed In-Domain Store Intent Keywords & Patterns
# ---------------------------------------------------------------------------
ALLOWED_BUSINESS_PATTERNS = [
    # Sales & Revenue
    r"\b(sale|sales|revenue|income|turnover|earning|earnings|profit|margin|gmv|upi|paytm|cash|transaction|transactions)\b",
    r"\b(বিক্রি|ಮಾರಾಟ|ಮಾರಾಟದ|बिक्री|कमाई|नफा|ಆದಾಯ|வருமானம்|விற்பனை|అమ్మకాలు|ఆదాయం|વેચાણ|નફો)\b",
    
    # Inventory, Stock & Products
    r"\b(stock|stocks|inventory|item|items|product|products|goods|sku|supply|supplier|restock|reorder|out of stock|expiry|expired)\b",
    r"\b(ದಾಸ್ತಾನು|ಸ್ಟಾಕ್|ಮಾಲು|सामान|इन्वेंट्री|स्टॉक|பொருட்கள்|சரக்கு|ఇన్వెంటరీ|స్టాక్|વસ્તુઓ|માલ|স্টক)\b",
    
    # Pricing, Discounts & Competitors
    r"\b(price|pricing|discount|cost|mrp|rate|competitor|deal|offer|promotion|margin|expensive|cheap)\b",
    r"\b(ಬೆಲೆ|ದರ|ರಿಯಾಯಿತಿ|कीमत|दाम|छूट|விலை|தள்ளுபடி|ధర|తగ్గింపు|ભાવ|વળતર|দাম|ছাড়)\b",
    
    # Customers & CRM
    r"\b(customer|customers|client|clients|buyer|buyers|footfall|khata|udhar|credit|loyalty|churn|winback)\b",
    r"\b(ಗ್ರಾಹಕ|ಗ್ರಾಹಕರು|ಖಾತೆ|ಉದ್ದರಿ|ग्राहक|उधार|खाता|வாடிக்கையாளர்|కస్టమర్|వినియోగదారు|ગ્રાહક|ক্রেতা)\b",
    
    # Business Telemetry & Pulse Features
    r"\b(nba|recommendation|recommendations|action|alert|brief|daily brief|settlement|soundbox|qr|qr code|pos)\b",
    r"\b(ಶಿಫಾರಸು|ಅನುಮೋದಿಸಿ|ಆರ್ಡರ್|ಹೌದು|ಖಂಡಿತ|ಮಾಡು|ಆಯ್ತು|सुझाव|मंजूर|करो|ஆர்டர்|అనుమతించు)\b",
    
    # Greetings & Common Store Queries
    r"^(hi|hello|hey|namaste|vanakkam|namaskara|namaskar|good morning|good evening|good afternoon|help|who are you|what can you do|who created you|status|summary)\b"
]

# ---------------------------------------------------------------------------
# Blocked Off-Domain Patterns (Coding, General Trivia, Politics, Jailbreaks)
# ---------------------------------------------------------------------------
BLOCKED_PATTERNS = [
    # 1. Prompt Injections & Jailbreaks
    r"(ignore\s+(all\s+)?previous\s+instructions)",
    r"(reveal\s+(your\s+)?(system\s+)?(prompt|instructions))",
    r"(system\s+instruction)",
    r"(dan\s+mode|jailbreak|unrestricted\s+mode|bypass\s+rules)",
    r"(act\s+as\s+an?\s+unfiltered)",
    r"(pretend\s+you\s+have\s+no\s+(rules|restrictions|guardrails))",
    
    # 2. Programming / Coding Requests
    r"\b(python|javascript|java|c\+\+|html|css|sql|rust|go|react|node|typescript|php|ruby|swift|kotlin)\b",
    r"(write\s+code|debug\s+this|create\s+a\s+function|create\s+a\s+class|drop\s+all\s+tables|drop\s+database)",
    r"(write\s+(a\s+)?(script|program|component|regex|algorithm))",
    r"(how\s+to\s+code\s+in)",
    r"\b(leetcode|hackerrank|binary\s+tree|binary\s+search|quicksort|fibonacci|recursion|stack\s+overflow)\b",
    
    # 3. General Trivia, History, Geography, Science
    r"(who\s+is\s+the\s+(president|prime\s+minister|king|queen|governor|actor|actress|director)\s+of)",
    r"(who\s+is\s+(the\s+)?(pm|president)\s+of)",
    r"(what\s+is\s+the\s+capital\s+of)",
    r"(how\s+many\s+planets)",
    r"(distance\s+between\s+(earth|moon|sun))",
    r"(speed\s+of\s+light)",
    r"(who\s+wrote\s+(the\s+book|hamlet|romeo))",
    r"(who\s+discovered\s+gravity)",
    r"\b(fifa|world\s+cup|olympics|ipl|oscars)\b",
    r"(who\s+won\s+.*(match|cup|game|tournament|election))",
    r"(tell\s+me\s+a\s+(story|poem|novel|fiction|fairy\s+tale|joke))",
    r"(write\s+(an\s+essay|a\s+poem|a\s+song|lyrics)\s+about)",
    r"(tell\s+me\s+a\s+poem)",
    
    # 4. Politics, Religion, Medical, Legal advice
    r"(who\s+should\s+i\s+vote\s+for)",
    r"(which\s+political\s+party\s+is\s+better)",
    r"(is\s+(bjp|congress|aap|democrat|republican)\s+good)",
    r"(how\s+to\s+cure|prescribe\s+medicine|treatment\s+for\s+cancer|fever\s+tablet|heavy\s+fever)",
    r"(legal\s+advice|filing\s+a\s+lawsuit|how\s+to\s+sue\s+someone)",
    
    # 5. Math Homework, Arithmetic & General Academic questions
    r"(solve\s+(the\s+equation|integral|derivative|calculus|\d+|[a-z]))",
    r"(\bderivative\s+of\b|\bintegral\s+of\b|\bsin\^2\s*\+\s*cos\^2\b)",
    r"(what\s+is\s+[a-z0-9]\s*[\+\-\*\/]\s*[a-z0-9])",
    r"(what\s+is\s+\d+\s*[\+\-\*\/]\s*\d+)",
    r"(calculate\s+[\d\+\-\*\/\^\(\)\s]+)",
    r"^[a-zA-Z0-9\s]*[\+\-\*\/=][a-zA-Z0-9\s]*$",
    r"\b(pythagoras|algebra|geometry|trigonometry|quadratic\s+equation)\b",
    
    # 6. Celebrity / Entertainment Gossip
    r"(who\s+is\s+(salman|shahrukh|virat|messi|ronaldo|taylor\s+swift|dhoni|kohli))",
    r"(movie\s+review\s+of|watch\s+free\s+movies)"
]

# Explicit allowed short conversational phrases
ALLOWED_SHORT_CONVERSATION = {
    "hi", "hello", "hey", "namaste", "namaskar", "vanakkam", "namaskara",
    "ok", "okay", "yes", "no", "haan", "ha", "nahi", "sure", "yep", "done",
    "thanks", "thank you", "dhanyawad", "shukriya", "nandri", "dhanyavadagalu",
    "help", "status", "summary", "daily brief", "insights", "actions", "details",
    "tell me more", "how much", "what to do", "kya karein", "yen madodu", "recommendations",
    "good morning", "good evening", "good afternoon"
}


def check_guardrails(query: str, language: str = "en") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Evaluates whether a user's query violates the store business boundary.
    
    Returns:
        (is_allowed: bool, refusal_response: Optional[str], violation_category: Optional[str])
    """
    if not query or not query.strip():
        return True, None, None

    cleaned = query.strip()
    lower_query = cleaned.lower()
    lang_key = (language or "en").lower()[:2]
    refusal_text = REFUSAL_MESSAGES.get(lang_key, REFUSAL_MESSAGES["en"])

    # 1. Check for explicitly blocked topics (Jailbreaks, Coding, Math, Trivia, Politics, Medical, etc.)
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, lower_query, re.IGNORECASE):
            logger.warning(f"Guardrail triggered for query: '{cleaned[:60]}' | Pattern: {pattern}")
            is_injection = any(k in pattern for k in ("previous", "jailbreak", "dan", "system", "rules", "unfiltered", "prompt", "instructions"))
            category = "PROMPT_INJECTION" if is_injection else "OFF_TOPIC"
            return False, refusal_text, category

    # 2. Check if query matches known store and business domains
    for pattern in ALLOWED_BUSINESS_PATTERNS:
        if re.search(pattern, lower_query, re.IGNORECASE):
            return True, None, None

    # 3. Check allowed short conversational keywords/confirmations
    if lower_query in ALLOWED_SHORT_CONVERSATION:
        return True, None, None

    # 4. If query is a general question or arithmetic without business terms, block as off-topic
    general_question_markers = [
        r"^who\s+(is|was|are|were)",
        r"^what\s+(is|was|are|were)",
        r"^where\s+(is|was|are|were)",
        r"^why\s+(is|was|are|were|do|does|did)",
        r"^how\s+to\s+(cook|make|build|drive|fly|learn|sing|dance)",
        r"^write\s+(a|an|me)?",
        r"^solve\s+",
        r"^explain\s+(quantum|relativity|photosynthesis|black\s+hole|history|physics|chemistry)",
        r"^tell\s+me\s+about\s+(the\s+universe|aliens|dinosaurs|movies|hollywood|bollywood|sports)"
    ]
    for g_pat in general_question_markers:
        if re.search(g_pat, lower_query, re.IGNORECASE):
            logger.warning(f"Guardrail triggered for generic non-business question: '{cleaned[:60]}'")
            return False, refusal_text, "OFF_TOPIC"

    # 5. For arbitrary math expressions (e.g. "a+b", "10 + 20", "x * y")
    if re.search(r"[\+\-\*\/\^=]", lower_query):
        logger.warning(f"Guardrail triggered for math expression: '{cleaned[:60]}'")
        return False, refusal_text, "OFF_TOPIC"

    # Default to allow if it appears store-related or ambiguous
    return True, None, None

