"""
Transaction risk scorer for Kavach 2.0.

Evaluates transaction risk based on multiple factors including
recipient history, amount, timing, and user demographics.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from loguru import logger

from app.models.transaction import Transaction, RiskLevel
from app.models.user import User


@dataclass
class TransactionRisk:
    """Risk assessment result for a transaction."""
    total_score: int  # 0-100+
    risk_level: RiskLevel
    factors: list[str]  # Human-readable factor descriptions
    recommendation: str  # Action recommendation


class RiskScorer:
    """
    Evaluates transaction risk based on multiple contextual factors.

    Scoring factors:
    - New recipient: +30 points
    - Amount > ₹10,000: +20 points
    - Amount > ₹50,000: +40 points
    - Initiated within 30 mins of incoming call: +25 points
    - Late night (11 PM - 6 AM): +10 points
    - User age > 50: +15 points
    - First-time digital user: +20 points
    """

    def score_transaction(
        self,
        transaction: Transaction,
        user: User,
        is_new_recipient: bool = True,
        recent_call: bool = False,
    ) -> TransactionRisk:
        """
        Calculate composite risk score for a transaction.

        Args:
            transaction: Transaction being evaluated.
            user: User initiating the transaction.
            is_new_recipient: Whether recipient is new (never transacted before).
            recent_call: Whether transaction was initiated within 30 mins of call.

        Returns:
            TransactionRisk with score, level, factors, and recommendation.
        """
        score = 0
        factors: list[str] = []

        # Factor 1: New recipient (+30)
        if is_new_recipient:
            score += 30
            factors.append("Recipient is new (never transacted before): +30")

        # Factor 2: Amount thresholds
        if transaction.amount > 50000:
            score += 40
            factors.append(f"High amount (₹{transaction.amount:,.0f} > ₹50,000): +40")
        elif transaction.amount > 10000:
            score += 20
            factors.append(f"Moderate amount (₹{transaction.amount:,.0f} > ₹10,000): +20")

        # Factor 3: Initiated after recent call (+25)
        if recent_call:
            score += 25
            factors.append("Transaction within 30 mins of incoming call: +25")

        # Factor 4: Late night transaction (+10)
        initiated_at = transaction.initiated_at or datetime.now(timezone.utc)
        hour = initiated_at.hour
        if hour >= 23 or hour < 6:
            score += 10
            factors.append(f"Late night transaction ({hour}:00 hours): +10")

        # Factor 5: User age > 50 (+15)
        if user.age and user.age > 50:
            score += 15
            factors.append(f"User age ({user.age}) > 50: +15")

        # Factor 6: First-time digital user (+20)
        if user.is_first_time_user:
            score += 20
            factors.append("First-time digital user: +20")

        # Cap score at 100
        total_score = min(score, 100)

        # Determine risk level
        risk_level = self._score_to_level(total_score)

        # Generate recommendation
        recommendation = self._get_recommendation(risk_level)

        logger.info(
            f"Risk score for {user.phone}: {total_score}/100 ({risk_level.value}) "
            f"| Amount: ₹{transaction.amount:,.0f} | Factors: {len(factors)}"
        )

        return TransactionRisk(
            total_score=total_score,
            risk_level=risk_level,
            factors=factors,
            recommendation=recommendation,
        )

    @staticmethod
    def _score_to_level(score: int) -> RiskLevel:
        """
        Map risk score to risk level.

        Args:
            score: Numeric risk score (0-100).

        Returns:
            RiskLevel enum value.
        """
        if score >= 76:
            return RiskLevel.CRITICAL
        if score >= 51:
            return RiskLevel.HIGH
        if score >= 26:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    @staticmethod
    def _get_recommendation(risk_level: RiskLevel) -> str:
        """
        Get action recommendation based on risk level.

        Args:
            risk_level: Assessed risk level.

        Returns:
            Human-readable recommendation string.
        """
        recommendations = {
            RiskLevel.LOW: "Transaction appears safe. Allow to proceed.",
            RiskLevel.MEDIUM: "Some risk factors present. Ask user clarifying questions.",
            RiskLevel.HIGH: "High risk detected. Alert trusted contact and pause transaction.",
            RiskLevel.CRITICAL: "Critical risk. Immediate alert + full recovery flow required.",
        }
        return recommendations[risk_level]


# Singleton instance
risk_scorer = RiskScorer()
