"""
Tests for the KavachAgent module.

Tests agent behavior with mock LLM responses for
LOW, HIGH, and CRITICAL risk scenarios.
"""

import pytest
from unittest.mock import patch, AsyncMock

from app.agent.kavach_agent import KavachAgent, AgentResponse
from app.agent.scam_detector import DetectionResult
from app.models.session import ConversationSession, SessionState
from app.models.transaction import Transaction, TransactionStatus, RiskLevel
from app.models.user import User


@pytest.fixture
def agent():
    """Create a KavachAgent instance."""
    return KavachAgent()


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = User(
        id=1,
        phone="+919999999999",
        name="Test User",
        language_preference="hi",
        trusted_contact_phone="+918888888888",
        trusted_contact_name="Trusted Contact",
        age=55,
        is_first_time_user=True,
    )
    return user


@pytest.fixture
def mock_session():
    """Create a mock conversation session."""
    session = ConversationSession(
        id=1,
        user_phone="+919999999999",
        state=SessionState.IDLE,
        messages=[],
        risk_score=0,
    )
    return session


@pytest.fixture
def mock_transaction():
    """Create a mock transaction."""
    return Transaction(
        id=1,
        user_phone="+919999999999",
        recipient_phone="+917777777777",
        amount=40000.0,
        status=TransactionStatus.PENDING,
    )


class TestAgentLowRisk:
    """Test agent behavior for LOW risk messages."""

    @pytest.mark.asyncio
    async def test_low_risk_continues_normally(
        self, agent, mock_user, mock_session
    ):
        """Agent should continue normally for safe messages."""
        low_risk_result = DetectionResult(
            risk_score=10,
            risk_level=RiskLevel.LOW,
            signals=[],
            reasoning="Normal conversation",
        )

        with patch(
            "app.agent.kavach_agent.scam_detector.detect",
            new_callable=AsyncMock,
            return_value=low_risk_result,
        ):
            response = await agent.process_message(
                phone="+919999999999",
                message="Hi, how are you?",
                session=mock_session,
                user=mock_user,
            )

        assert response.action == "CONTINUE"
        assert response.risk_level == RiskLevel.LOW
        assert response.should_alert_contact is False
        assert response.should_start_recovery is False


class TestAgentHighRisk:
    """Test agent behavior for HIGH risk messages."""

    @pytest.mark.asyncio
    async def test_high_risk_asks_followup(
        self, agent, mock_user, mock_session
    ):
        """Agent should ask follow-up questions for HIGH risk."""
        high_risk_result = DetectionResult(
            risk_score=65,
            risk_level=RiskLevel.HIGH,
            signals=["AUTHORITY_IMPERSONATION", "URGENCY"],
            reasoning="Government impersonation detected",
        )

        with patch(
            "app.agent.kavach_agent.scam_detector.detect",
            new_callable=AsyncMock,
            return_value=high_risk_result,
        ):
            response = await agent.process_message(
                phone="+919999999999",
                message="CBI ne mujhe call kiya hai",
                session=mock_session,
                user=mock_user,
            )

        assert response.action == "QUESTION"
        assert response.risk_level == RiskLevel.HIGH
        assert response.should_alert_contact is True
        assert mock_session.state == SessionState.QUESTIONING


class TestAgentCriticalRisk:
    """Test agent behavior for CRITICAL risk messages."""

    @pytest.mark.asyncio
    async def test_critical_risk_triggers_recovery(
        self, agent, mock_user, mock_session
    ):
        """Agent should trigger full recovery for CRITICAL risk."""
        critical_result = DetectionResult(
            risk_score=90,
            risk_level=RiskLevel.CRITICAL,
            signals=["DIGITAL_ARREST", "ISOLATION", "FINANCIAL_DEMAND"],
            reasoning="Active digital arrest scam in progress",
        )

        with patch(
            "app.agent.kavach_agent.scam_detector.detect",
            new_callable=AsyncMock,
            return_value=critical_result,
        ):
            response = await agent.process_message(
                phone="+919999999999",
                message="Main digital arrest mein hoon, paisa transfer karna hai",
                session=mock_session,
                user=mock_user,
            )

        assert response.action == "RECOVERY"
        assert response.risk_level == RiskLevel.CRITICAL
        assert response.should_alert_contact is True
        assert response.should_start_recovery is True
        assert mock_session.state == SessionState.CONFIRMED_RISK


class TestAgentQuestioningState:
    """Test agent behavior during QUESTIONING state."""

    @pytest.mark.asyncio
    async def test_affirmative_response_triggers_recovery(
        self, agent, mock_user, mock_session
    ):
        """User saying 'yes' during questioning should ask scam type then trigger recovery."""
        mock_session.state = SessionState.QUESTIONING
        mock_session.risk_score = 60

        low_result = DetectionResult(
            risk_score=10,
            risk_level=RiskLevel.LOW,
            signals=[],
            reasoning="Simple affirmative",
        )

        with patch(
            "app.agent.kavach_agent.scam_detector.detect",
            new_callable=AsyncMock,
            return_value=low_result,
        ):
            response = await agent.process_message(
                phone="+919999999999",
                message="1",  # User confirms pressure
                session=mock_session,
                user=mock_user,
            )

        # Now asks scam type (not immediate recovery)
        assert response.action == "ASK_SCAM_TYPE"
        assert response.risk_level == RiskLevel.CRITICAL
        assert response.should_alert_contact is True
        assert mock_session.state == SessionState.CONFIRMED_RISK

    @pytest.mark.asyncio
    async def test_negative_response_marks_safe(
        self, agent, mock_user, mock_session
    ):
        """User saying 'no' during questioning should mark as safe."""
        mock_session.state = SessionState.QUESTIONING

        low_result = DetectionResult(
            risk_score=5,
            risk_level=RiskLevel.LOW,
            signals=[],
            reasoning="Negative response",
        )

        with patch(
            "app.agent.kavach_agent.scam_detector.detect",
            new_callable=AsyncMock,
            return_value=low_result,
        ):
            response = await agent.process_message(
                phone="+919999999999",
                message="2",  # User says no pressure
                session=mock_session,
                user=mock_user,
            )

        assert response.action == "SAFE"
        assert response.risk_level == RiskLevel.LOW
        assert response.should_alert_contact is False
        assert mock_session.state == SessionState.CONFIRMED_SAFE


class TestAgentMessageTracking:
    """Test that agent tracks conversation history."""

    @pytest.mark.asyncio
    async def test_messages_recorded_in_session(
        self, agent, mock_user, mock_session
    ):
        """Agent should record user and agent messages in session."""
        low_result = DetectionResult(
            risk_score=5,
            risk_level=RiskLevel.LOW,
            signals=[],
            reasoning="Safe",
        )

        with patch(
            "app.agent.kavach_agent.scam_detector.detect",
            new_callable=AsyncMock,
            return_value=low_result,
        ):
            await agent.process_message(
                phone="+919999999999",
                message="Hello",
                session=mock_session,
                user=mock_user,
            )

        assert mock_session.get_message_count() == 2  # user + agent
        assert mock_session.messages[0]["role"] == "user"
        assert mock_session.messages[0]["content"] == "Hello"
        assert mock_session.messages[1]["role"] == "agent"
