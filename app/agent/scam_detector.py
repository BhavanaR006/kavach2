"""
Scam detection engine for Kavach 2.0.

Uses Claude AI with a carefully engineered prompt to identify coercion signals,
authority impersonation, and known Indian scam patterns. Includes a fallback
keyword-based detector for API failure scenarios.
"""

import json
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from app.integrations.claude_client import claude_client
from app.models.transaction import RiskLevel


@dataclass
class DetectionResult:
    """Result of scam detection analysis."""
    risk_score: int = 0  # 0-100
    risk_level: RiskLevel = RiskLevel.LOW
    signals: list[str] = field(default_factory=list)
    reasoning: str = ""


# System prompt for Claude scam detection
SCAM_DETECTION_SYSTEM_PROMPT = """You are Kavach 2.0's fraud detection AI. Your job is to analyze messages for signs of scam or coercion targeting Indian users.

COERCION SIGNALS TO DETECT:
1. Fear induction ("your account will be blocked", "you will be arrested")
2. Authority impersonation (CBI, police, RBI, court, income tax, customs)
3. Urgency manufacturing ("do it now", "only 10 minutes left", "deadline today")
4. Isolation instruction ("don't tell anyone", "this is confidential", "secret investigation")
5. OTP/money demand ("send OTP", "transfer money", "pay fine")
6. Emotional manipulation ("your son is in jail", "accident occurred")

KNOWN INDIAN SCAM PATTERNS:
- Digital Arrest: "You are under digital arrest, stay on video call"
- KYC Freeze: "Your KYC is expiring, bank account will be frozen"
- Aadhaar Suspension: "Your Aadhaar is linked to a crime, will be suspended"
- Fake Police/CBI: "This is CBI/police, a case is filed against you"
- Lottery/Prize: "You've won X lakhs, pay processing fee"
- Fake Job Offer: "Work from home, invest money first to start earning"
- Customs Parcel: "Drugs found in your parcel at customs"
- Loan Pre-approval: "Pre-approved loan, just pay processing charges"

INPUT LANGUAGES: Hindi, Telugu, Tamil, Bengali, English, Hinglish (Hindi+English mix)

RESPOND WITH ONLY VALID JSON in this format:
{
    "risk_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "signals": ["<signal_1>", "<signal_2>"],
    "reasoning": "<brief explanation>"
}

SCORING GUIDE:
- 0-25 (LOW): Normal conversation, no coercion signals
- 26-50 (MEDIUM): Mild pressure or suspicious elements, needs clarification
- 51-75 (HIGH): Clear coercion signals, likely scam
- 76-100 (CRITICAL): Multiple strong signals, active scam in progress"""


# Fallback keyword detection patterns
FALLBACK_KEYWORDS: dict[str, list[str]] = {
    "AUTHORITY_IMPERSONATION": [
        "cbi", "police", "rbi", "court", "income tax", "customs",
        "officer", "inspector", "commissioner", "warrant",
        "पुलिस", "अधिकारी", "कोर्ट", "गिरफ्तार",
        "పోలీసు", "అధికారి", "கோர்ட்", "போலீஸ்",
    ],
    "URGENCY": [
        "immediately", "urgent", "now", "deadline", "last chance",
        "abhi", "turant", "jaldi", "fauran",
        "तुरंत", "अभी", "जल्दी", "आखिरी मौका",
    ],
    "DIGITAL_ARREST": [
        "digital arrest", "video call", "don't disconnect",
        "डिजिटल अरेस्ट", "वीडियो कॉल",
    ],
    "KYC_FRAUD": [
        "kyc", "aadhaar", "aadhar", "pan card", "bank frozen",
        "account block", "suspend", "expire",
        "केवाईसी", "आधार", "बैंक बंद", "खाता बंद",
    ],
    "FINANCIAL_DEMAND": [
        "transfer", "send money", "pay fine", "otp", "upi",
        "processing fee", "advance payment",
        "पैसे भेजो", "ट्रांसफर करो", "जुर्माना",
    ],
    "ISOLATION": [
        "don't tell", "secret", "confidential", "don't inform",
        "किसी को मत बताना", "गोपनीय", "रहस्य",
    ],
}


class ScamDetector:
    """
    Scam detection engine using Claude AI with keyword fallback.

    Analyzes messages for coercion signals, authority impersonation,
    and known Indian fraud patterns across multiple languages.
    """

    async def detect(
        self,
        message: str,
        context: Optional[dict] = None,
        language: str = "en",
    ) -> DetectionResult:
        """
        Analyze a message for scam indicators.

        Uses Claude AI as primary detector with keyword-based fallback
        if the API call fails.

        Args:
            message: User's message text to analyze.
            context: Additional context (conversation history, transaction details).
            language: Detected language code.

        Returns:
            DetectionResult with risk score, level, signals, and reasoning.
        """
        try:
            return await self._detect_with_claude(message, context, language)
        except Exception as e:
            logger.warning(f"Claude detection failed, using keyword fallback: {e}")
            return self._detect_with_keywords(message)

    async def _detect_with_claude(
        self,
        message: str,
        context: Optional[dict],
        language: str,
    ) -> DetectionResult:
        """
        Use Claude AI for intelligent scam detection.

        Args:
            message: Message to analyze.
            context: Conversation context.
            language: Language code.

        Returns:
            DetectionResult from Claude's analysis.
        """
        # Build user message with context
        user_prompt = f"Language: {language}\n"
        if context:
            user_prompt += f"Context: {json.dumps(context, ensure_ascii=False)}\n"
        user_prompt += f"\nMessage to analyze:\n{message}"

        result = await claude_client.complete_json(
            system=SCAM_DETECTION_SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=500,
        )

        risk_score = int(result.get("risk_score", 0))
        risk_level_str = result.get("risk_level", "LOW")

        try:
            risk_level = RiskLevel(risk_level_str)
        except ValueError:
            risk_level = self._score_to_level(risk_score)

        return DetectionResult(
            risk_score=risk_score,
            risk_level=risk_level,
            signals=result.get("signals", []),
            reasoning=result.get("reasoning", ""),
        )

    def _detect_with_keywords(self, message: str) -> DetectionResult:
        """
        Fallback keyword-based scam detection.

        Checks message against known scam keywords across categories.

        Args:
            message: Message to analyze.

        Returns:
            DetectionResult based on keyword matches.
        """
        message_lower = message.lower()
        detected_signals: list[str] = []
        total_score = 0

        category_scores = {
            "AUTHORITY_IMPERSONATION": 30,
            "URGENCY": 15,
            "DIGITAL_ARREST": 40,
            "KYC_FRAUD": 25,
            "FINANCIAL_DEMAND": 25,
            "ISOLATION": 20,
        }

        for category, keywords in FALLBACK_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in message_lower:
                    signal = f"{category}: matched '{keyword}'"
                    if signal not in detected_signals:
                        detected_signals.append(signal)
                        total_score += category_scores.get(category, 10)
                    break  # Only count each category once

        # Cap at 100
        risk_score = min(total_score, 100)
        risk_level = self._score_to_level(risk_score)

        reasoning = (
            f"Keyword-based detection (Claude unavailable). "
            f"Found {len(detected_signals)} signal categories."
        )

        return DetectionResult(
            risk_score=risk_score,
            risk_level=risk_level,
            signals=detected_signals,
            reasoning=reasoning,
        )

    @staticmethod
    def _score_to_level(score: int) -> RiskLevel:
        """
        Convert numeric risk score to risk level.

        Args:
            score: Risk score 0-100.

        Returns:
            Corresponding RiskLevel enum value.
        """
        if score >= 76:
            return RiskLevel.CRITICAL
        if score >= 51:
            return RiskLevel.HIGH
        if score >= 26:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


# Singleton instance
scam_detector = ScamDetector()
