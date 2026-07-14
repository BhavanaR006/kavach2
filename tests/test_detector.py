"""
Tests for the ScamDetector module.

Tests keyword-based fallback detection with sample scam messages
in Hindi and English across multiple pattern categories.
"""

import pytest

from app.agent.scam_detector import ScamDetector, DetectionResult
from app.models.transaction import RiskLevel


@pytest.fixture
def detector():
    """Create a ScamDetector instance."""
    return ScamDetector()


class TestKeywordDetection:
    """Test the keyword-based fallback detector."""

    def test_authority_impersonation_english(self, detector: ScamDetector):
        """Detect authority impersonation in English message."""
        message = "This is CBI calling. A case has been filed against you."
        result = detector._detect_with_keywords(message)

        assert result.risk_score > 0
        assert len(result.signals) > 0
        assert any("AUTHORITY_IMPERSONATION" in s for s in result.signals)

    def test_authority_impersonation_hindi(self, detector: ScamDetector):
        """Detect authority impersonation in Hindi message."""
        message = "Yeh police se bol rahe hain. Aapke khilaf warrant jari hua hai."
        result = detector._detect_with_keywords(message)

        assert result.risk_score > 0
        assert any("AUTHORITY_IMPERSONATION" in s for s in result.signals)

    def test_digital_arrest_english(self, detector: ScamDetector):
        """Detect digital arrest scam in English."""
        message = "You are under digital arrest. Do not disconnect this video call."
        result = detector._detect_with_keywords(message)

        assert result.risk_score >= 40
        assert result.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}
        assert any("DIGITAL_ARREST" in s for s in result.signals)

    def test_digital_arrest_hindi(self, detector: ScamDetector):
        """Detect digital arrest scam in Hindi."""
        message = "Aap digital arrest mein hain. Video call disconnect mat karein."
        result = detector._detect_with_keywords(message)

        assert result.risk_score >= 40
        assert any("DIGITAL_ARREST" in s for s in result.signals)

    def test_kyc_fraud_english(self, detector: ScamDetector):
        """Detect KYC fraud pattern."""
        message = "Your KYC is expired. Bank account will be suspended."
        result = detector._detect_with_keywords(message)

        assert result.risk_score > 0
        assert any("KYC_FRAUD" in s for s in result.signals)

    def test_financial_demand_english(self, detector: ScamDetector):
        """Detect financial demand / OTP request."""
        message = "Send OTP to verify your account. Transfer processing fee now."
        result = detector._detect_with_keywords(message)

        assert result.risk_score > 0
        assert any("FINANCIAL_DEMAND" in s for s in result.signals)

    def test_isolation_hindi(self, detector: ScamDetector):
        """Detect isolation instruction in Hindi."""
        message = "Kisi ko mat batana. Yeh confidential investigation hai."
        result = detector._detect_with_keywords(message)

        assert result.risk_score > 0
        assert any("ISOLATION" in s for s in result.signals)

    def test_urgency_english(self, detector: ScamDetector):
        """Detect urgency manufacturing."""
        message = "You must act immediately. This is urgent. Last chance to respond."
        result = detector._detect_with_keywords(message)

        assert result.risk_score > 0
        assert any("URGENCY" in s for s in result.signals)

    def test_multiple_signals_compound(self, detector: ScamDetector):
        """Detect multiple signal categories in one message."""
        message = (
            "This is CBI. You are under digital arrest. "
            "Transfer money immediately. Don't tell anyone."
        )
        result = detector._detect_with_keywords(message)

        assert result.risk_score >= 76
        assert result.risk_level == RiskLevel.CRITICAL
        assert len(result.signals) >= 3

    def test_safe_message_low_score(self, detector: ScamDetector):
        """Ensure normal messages get LOW risk."""
        message = "Hi, how are you? Can we meet for lunch tomorrow?"
        result = detector._detect_with_keywords(message)

        assert result.risk_score == 0
        assert result.risk_level == RiskLevel.LOW
        assert len(result.signals) == 0

    def test_safe_transaction_message(self, detector: ScamDetector):
        """Normal payment discussion should be LOW risk."""
        message = "Please send me the money for dinner we had yesterday."
        result = detector._detect_with_keywords(message)

        # Should be low - normal conversation about money
        assert result.risk_level == RiskLevel.LOW

    def test_score_capped_at_100(self, detector: ScamDetector):
        """Risk score should never exceed 100."""
        message = (
            "CBI police RBI digital arrest video call "
            "transfer money OTP immediately urgent "
            "don't tell anyone KYC Aadhaar suspend"
        )
        result = detector._detect_with_keywords(message)

        assert result.risk_score <= 100


class TestScoreToLevel:
    """Test score-to-level conversion."""

    def test_low_score(self, detector: ScamDetector):
        assert detector._score_to_level(0) == RiskLevel.LOW
        assert detector._score_to_level(25) == RiskLevel.LOW

    def test_medium_score(self, detector: ScamDetector):
        assert detector._score_to_level(26) == RiskLevel.MEDIUM
        assert detector._score_to_level(50) == RiskLevel.MEDIUM

    def test_high_score(self, detector: ScamDetector):
        assert detector._score_to_level(51) == RiskLevel.HIGH
        assert detector._score_to_level(75) == RiskLevel.HIGH

    def test_critical_score(self, detector: ScamDetector):
        assert detector._score_to_level(76) == RiskLevel.CRITICAL
        assert detector._score_to_level(100) == RiskLevel.CRITICAL
