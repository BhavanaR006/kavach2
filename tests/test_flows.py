"""
Tests for DetectFlow state machine transitions.

Verifies the detection flow correctly transitions between states
and produces appropriate responses at each stage.
"""

import pytest
from unittest.mock import patch, AsyncMock

from app.flows.detect_flow import DetectFlow
from app.agent.scam_detector import DetectionResult
from app.models.session import ConversationSession, SessionState
from app.models.transaction import Transaction, TransactionStatus, RiskLevel
from app.models.user import User


@pytest.fixture
def flow():
    """Create a DetectFlow instance."""
    return DetectFlow()


@pytest.fixture
def user():
    """Create a test user."""
    return User(
        id=1,
        phone="+919999999999",
        name="Test User",
        language_preference="hi",
        trusted_contact_phone="+918888888888",
        trusted_contact_name="Family Member",
        age=55,
        is_first_time_user=True,
    )


@pytest.fixture
def session():
    """Create a test session in IDLE state."""
    return ConversationSession(
        id=1,
        user_phone="+919999999999",
        state=SessionState.IDLE,
        messages=[],
        risk_score=0,
    )


@pytest.fixture
def transaction():
    """Create a test transaction."""
    return Transaction(
        id=1,
        user_phone="+919999999999",
        recipient_phone="+917777777777",
        amount=40000.0,
        status=TransactionStatus.PENDING,
    )


class TestDetectFlowInitiation:
    """Test detection flow initiation."""

    @pytest.mark.asyncio
    async def test_initiate_sets_transaction_detected(
        self, flow, transaction, user, session
    ):
        """Initiating flow should move session to TRANSACTION_DETECTED."""
        response = await flow.initiate(transaction, user, session)

        assert session.state == SessionState.TRANSACTION_DETECTED
        assert session.transaction_id == transaction.id
        assert response.action == "QUESTION"
        assert response.risk_score > 0

    @pytest.mark.asyncio
    async def test_initiate_flags_transaction(
        self, flow, transaction, user, session
    ):
        """Initiation should flag the transaction."""
        await flow.initiate(transaction, user, session)

        assert transaction.status == TransactionStatus.FLAGGED
        assert transaction.risk_score > 0

    @pytest.mark.asyncio
    async def test_initiate_sends_hindi_question(
        self, flow, transaction, user, session
    ):
        """Question should be in user's preferred language (Hindi)."""
        user.language_preference = "hi"
        response = await flow.initiate(transaction, user, session)

        # Hindi question should contain the amount
        assert "40,000" in response.message
        assert response.message  # Non-empty

    @pytest.mark.asyncio
    async def test_initiate_high_risk_alerts_contact(
        self, flow, transaction, user, session
    ):
        """High-risk transaction should signal alert to contact."""
        # High amount + first-time user + age > 50 = HIGH risk
        transaction.amount = 60000.0
        response = await flow.initiate(transaction, user, session)

        assert response.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        assert response.should_alert_contact is True

    @pytest.mark.asyncio
    async def test_initiate_low_amount_lower_risk(
        self, flow, user, session
    ):
        """Low-amount transaction should have lower risk score."""
        low_txn = Transaction(
            id=2,
            user_phone="+919999999999",
            recipient_phone="+917777777777",
            amount=500.0,
            status=TransactionStatus.PENDING,
        )
        user.age = 25
        user.is_first_time_user = False

        response = await flow.initiate(low_txn, user, session)

        # New recipient still adds 30, but no other big factors
        assert response.risk_score < 76


class TestDetectFlowStateTransitions:
    """Test state machine transitions."""

    @pytest.mark.asyncio
    async def test_process_response_affirmative(
        self, flow, transaction, user, session
    ):
        """Affirmative response should move to CONFIRMED_RISK."""
        session.state = SessionState.QUESTIONING
        session.risk_score = 60

        low_result = DetectionResult(
            risk_score=10, risk_level=RiskLevel.LOW, signals=[], reasoning=""
        )

        with patch(
            "app.agent.kavach_agent.scam_detector.detect",
            new_callable=AsyncMock,
            return_value=low_result,
        ):
            response = await flow.process_response(
                message="haan",
                session=session,
                transaction=transaction,
                user=user,
            )

        assert session.state == SessionState.CONFIRMED_RISK
        assert response.should_start_recovery is True

    @pytest.mark.asyncio
    async def test_process_response_negative(
        self, flow, transaction, user, session
    ):
        """Negative response should move to CONFIRMED_SAFE."""
        session.state = SessionState.QUESTIONING

        low_result = DetectionResult(
            risk_score=5, risk_level=RiskLevel.LOW, signals=[], reasoning=""
        )

        with patch(
            "app.agent.kavach_agent.scam_detector.detect",
            new_callable=AsyncMock,
            return_value=low_result,
        ):
            response = await flow.process_response(
                message="nahi",
                session=session,
                transaction=transaction,
                user=user,
            )

        assert session.state == SessionState.CONFIRMED_SAFE
        assert response.action == "SAFE"
        assert response.should_start_recovery is False


class TestDetectFlowHelpers:
    """Test helper methods."""

    def test_is_active_questioning(self, flow, session):
        """Session in QUESTIONING should be active."""
        session.state = SessionState.QUESTIONING
        assert flow.is_active(session) is True

    def test_is_active_transaction_detected(self, flow, session):
        """Session in TRANSACTION_DETECTED should be active."""
        session.state = SessionState.TRANSACTION_DETECTED
        assert flow.is_active(session) is True

    def test_is_not_active_idle(self, flow, session):
        """Session in IDLE should not be active."""
        session.state = SessionState.IDLE
        assert flow.is_active(session) is False

    def test_is_not_active_resolved(self, flow, session):
        """Session in RESOLVED should not be active."""
        session.state = SessionState.RESOLVED
        assert flow.is_active(session) is False

    def test_get_current_state(self, flow, session):
        """Should return current session state."""
        session.state = SessionState.QUESTIONING
        assert flow.get_current_state(session) == SessionState.QUESTIONING
