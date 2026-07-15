"""
Language utility functions for Kavach 2.0.

Provides script detection, greetings, and localized Kavach messages
for Hindi, Telugu, Tamil, Bengali, and English.
"""

from typing import Optional


# Supported languages with display names
SUPPORTED_LANGUAGES: dict[str, str] = {
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "bn": "Bengali",
    "en": "English",
}

# Language-specific greetings
GREETINGS: dict[str, str] = {
    "hi": "नमस्ते",
    "te": "నమస్కారం",
    "ta": "வணக்கம்",
    "bn": "নমস্কার",
    "en": "Hello",
}

# Kavach introduction messages per language
KAVACH_INTROS: dict[str, str] = {
    "hi": (
        "🛡️ नमस्ते! मैं Kavach 2.0 हूँ — आपका डिजिटल सुरक्षा साथी। "
        "मैं आपको ऑनलाइन फ्रॉड से बचाने के लिए यहाँ हूँ।"
    ),
    "te": (
        "🛡️ నమస్కారం! నేను Kavach 2.0 — మీ డిజిటల్ భద్రతా సహాయకుడిని. "
        "ఆన్‌లైన్ మోసాల నుండి మిమ్మల్ని రక్షించడానికి నేను ఇక్కడ ఉన్నాను."
    ),
    "ta": (
        "🛡️ வணக்கம்! நான் Kavach 2.0 — உங்கள் டிஜிட்டல் பாதுகாப்பு உதவியாளர். "
        "ஆன்லைன் மோசடிகளிலிருந்து உங்களைக் காக்க நான் இங்கே இருக்கிறேன்."
    ),
    "bn": (
        "🛡️ নমস্কার! আমি Kavach 2.0 — আপনার ডিজিটাল সুরক্ষা সহায়ক। "
        "অনলাইন জালিয়াতি থেকে আপনাকে রক্ষা করতে আমি এখানে আছি।"
    ),
    "en": (
        "🛡️ Hello! I'm Kavach 2.0 — your digital safety companion. "
        "I'm here to protect you from online fraud."
    ),
}

# Transaction interception questions per language
TRANSACTION_QUESTIONS: dict[str, str] = {
    "hi": (
        "⚠️ Kavach ने देखा आप ₹{amount} transfer करने वाले हैं एक नये account में। "
        "क्या आपको किसी ने इस payment के लिए force किया है?\n\n"
        "1️⃣ हाँ (Yes)\n2️⃣ नहीं (No)"
    ),
    "te": (
        "⚠️ Kavach గమనించింది: మీరు ₹{amount} కొత్త ఖాతాకు బదిలీ చేయబోతున్నారు। "
        "ఈ చెల్లింపు కోసం ఎవరైనా మిమ్మల్ని బలవంతం చేశారా?\n\n"
        "1️⃣ అవును (Yes)\n2️⃣ కాదు (No)"
    ),
    "ta": (
        "⚠️ Kavach கவனித்தது: நீங்கள் ₹{amount} புதிய கணக்கிற்கு மாற்ற உள்ளீர்கள். "
        "இந்த பணம் செலுத்த யாராவது உங்களை கட்டாயப்படுத்தினார்களா?\n\n"
        "1️⃣ ஆம் (Yes)\n2️⃣ இல்லை (No)"
    ),
    "bn": (
        "⚠️ Kavach লক্ষ্য করেছে: আপনি ₹{amount} একটি নতুন অ্যাকাউন্টে ট্রান্সফার করতে "
        "যাচ্ছেন। এই পেমেন্টের জন্য কি কেউ আপনাকে জোর করেছে?\n\n"
        "1️⃣ হ্যাঁ (Yes)\n2️⃣ না (No)"
    ),
    "en": (
        "⚠️ Kavach noticed you are about to transfer ₹{amount} to a new account. "
        "Has someone pressured you into making this payment?\n\n"
        "1️⃣ Yes\n2️⃣ No"
    ),
}

# Follow-up question about government officer calls
FOLLOWUP_QUESTIONS: dict[str, str] = {
    "hi": (
        "🤔 क्या किसी government officer, police, CBI, या RBI ने आपको call किया था "
        "और कहा कि आपका account/Aadhaar freeze हो जाएगा?\n\n"
        "1️⃣ हाँ (Yes)\n2️⃣ नहीं (No)"
    ),
    "te": (
        "🤔 ఏదైనా ప్రభుత్వ అధికారి, పోలీసు, CBI, లేదా RBI మీకు కాల్ చేసి "
        "మీ ఖాతా/ఆధార్ ఫ్రీజ్ అవుతుందని చెప్పారా?\n\n"
        "1️⃣ అవును (Yes)\n2️⃣ కాదు (No)"
    ),
    "ta": (
        "🤔 ஏதேனும் அரசு அதிகாரி, போலீஸ், CBI, அல்லது RBI உங்களை அழைத்து "
        "உங்கள் கணக்கு/ஆதார் முடக்கப்படும் என்று சொன்னார்களா?\n\n"
        "1️⃣ ஆம் (Yes)\n2️⃣ இல்லை (No)"
    ),
    "bn": (
        "🤔 কোনো সরকারি অফিসার, পুলিশ, CBI, বা RBI আপনাকে কল করে বলেছে "
        "যে আপনার অ্যাকাউন্ট/আধার ফ্রিজ হয়ে যাবে?\n\n"
        "1️⃣ হ্যাঁ (Yes)\n2️⃣ না (No)"
    ),
    "en": (
        "🤔 Did any government officer, police, CBI, or RBI call you and say "
        "your account/Aadhaar will be frozen?\n\n"
        "1️⃣ Yes\n2️⃣ No"
    ),
}


def detect_script(text: str) -> str:
    """
    Detect the script used in the given text.

    Checks Unicode code points to identify Devanagari, Telugu,
    Tamil, or Bengali scripts.

    Args:
        text: Input text to analyze.

    Returns:
        Language code (hi, te, ta, bn, en) based on detected script.
    """
    script_ranges = {
        "hi": (0x0900, 0x097F),  # Devanagari
        "te": (0x0C00, 0x0C7F),  # Telugu
        "ta": (0x0B80, 0x0BFF),  # Tamil
        "bn": (0x0980, 0x09FF),  # Bengali
    }

    char_counts: dict[str, int] = {lang: 0 for lang in script_ranges}

    for char in text:
        code_point = ord(char)
        for lang, (start, end) in script_ranges.items():
            if start <= code_point <= end:
                char_counts[lang] += 1
                break

    # Return language with most matching characters
    max_lang = max(char_counts, key=char_counts.get)  # type: ignore
    if char_counts[max_lang] > 0:
        return max_lang

    return "en"  # Default to English for Latin script


def get_greeting(language: str) -> str:
    """
    Get a localized greeting.

    Args:
        language: Language code (hi, te, ta, bn, en).

    Returns:
        Greeting string in the specified language.
    """
    return GREETINGS.get(language, GREETINGS["en"])


def get_kavach_intro(language: str) -> str:
    """
    Get the Kavach introduction message in the specified language.

    Args:
        language: Language code (hi, te, ta, bn, en).

    Returns:
        Kavach intro message in the specified language.
    """
    return KAVACH_INTROS.get(language, KAVACH_INTROS["en"])


def get_transaction_question(language: str, amount: float) -> str:
    """
    Get the transaction interception question in the specified language.

    Args:
        language: Language code.
        amount: Transaction amount in INR.

    Returns:
        Formatted question string.
    """
    template = TRANSACTION_QUESTIONS.get(language, TRANSACTION_QUESTIONS["en"])
    return template.format(amount=f"{amount:,.0f}")


def get_followup_question(language: str) -> str:
    """
    Get the follow-up question about government officer calls.

    Args:
        language: Language code.

    Returns:
        Follow-up question in the specified language.
    """
    return FOLLOWUP_QUESTIONS.get(language, FOLLOWUP_QUESTIONS["en"])


def is_affirmative(text: str) -> bool:
    """
    Check if user response is affirmative (yes/haan/avunu etc.).

    Args:
        text: User's response text.

    Returns:
        True if the response indicates 'yes'.
    """
    affirmative_words = {
        "1", "yes", "haan", "ha", "haa", "ji", "yes",
        "avunu", "aam", "hyan", "হ্যাঁ", "हाँ", "हां",
        "అవును", "ஆம்",
    }
    return text.strip().lower() in affirmative_words


def is_negative(text: str) -> bool:
    """
    Check if user response is negative (no/nahi/ledu etc.).

    Args:
        text: User's response text.

    Returns:
        True if the response indicates 'no'.
    """
    negative_words = {
        "2", "no", "nahi", "naa", "na",
        "ledu", "illa", "না", "नहीं",
        "లేదు", "இல்லை",
    }
    return text.strip().lower() in negative_words


# Scam type selection question (asked after user confirms pressure)
SCAM_TYPE_QUESTIONS: dict[str, str] = {
    "hi": "Kavach aapki madad karega. Batayein kya hua — neeche se chunein:",
    "te": "Kavach మీకు సహాయం చేస్తుంది. ఏం జరిగిందో చెప్పండి:",
    "ta": "Kavach உங்களுக்கு உதவும். என்ன நடந்தது சொல்லுங்கள்:",
    "bn": "Kavach আপনাকে সাহায্য করবে। কী হয়েছে জানান:",
    "en": "Kavach will help you. Tell us what happened — select below:",
}

# Detailed scam options for WhatsApp list message
SCAM_OPTIONS: list[dict] = [
    {"id": "digital_arrest", "title": "Digital Arrest", "description": "Someone on video call says I'm under arrest"},
    {"id": "fake_police", "title": "Fake Police/CBI Call", "description": "Officer threatening arrest, asking money"},
    {"id": "fake_rbi", "title": "Fake RBI/Bank Call", "description": "Says account will be frozen/blocked"},
    {"id": "kyc_expiry", "title": "KYC/Aadhaar Threat", "description": "KYC expired, Aadhaar suspended, send OTP"},
    {"id": "otp_demand", "title": "OTP/Money Demand", "description": "Someone asking for OTP or transfer"},
    {"id": "customs_parcel", "title": "Customs/Parcel Scam", "description": "Drugs found in your parcel, pay fine"},
    {"id": "lottery_prize", "title": "Lottery/Prize Won", "description": "Pay processing fee to claim prize"},
    {"id": "job_offer", "title": "Fake Job Offer", "description": "Invest money first to start earning"},
    {"id": "loan_offer", "title": "Loan Pre-approved", "description": "Pay charges to activate loan"},
    {"id": "other", "title": "Something Else", "description": "None of the above, will type"},
]

# Scam type mapping from user's choice
SCAM_TYPE_MAP: dict[str, str] = {
    "1": "DIGITAL_ARREST",
    "2": "AUTHORITY_IMPERSONATION",
    "3": "AUTHORITY_IMPERSONATION",
    "4": "KYC_FRAUD",
    "5": "FINANCIAL_DEMAND",
    "6": "DIGITAL_ARREST",
    "7": "FINANCIAL_DEMAND",
    "8": "FINANCIAL_DEMAND",
    "9": "FINANCIAL_DEMAND",
    "10": "OTHER",
    "digital_arrest": "DIGITAL_ARREST",
    "fake_police": "AUTHORITY_IMPERSONATION",
    "fake_rbi": "AUTHORITY_IMPERSONATION",
    "kyc_expiry": "KYC_FRAUD",
    "otp_demand": "FINANCIAL_DEMAND",
    "customs_parcel": "DIGITAL_ARREST",
    "lottery_prize": "FINANCIAL_DEMAND",
    "job_offer": "FINANCIAL_DEMAND",
    "loan_offer": "FINANCIAL_DEMAND",
    "other": "OTHER",
}


def get_scam_type_question(language: str) -> str:
    """Get the scam type question text in user's language."""
    return SCAM_TYPE_QUESTIONS.get(language, SCAM_TYPE_QUESTIONS["en"])


def get_scam_options_for_list() -> list[dict]:
    """Get scam options formatted for WhatsApp list message."""
    return [
        {
            "title": "Select what happened",
            "rows": SCAM_OPTIONS,
        }
    ]
