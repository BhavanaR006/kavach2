"""
Detection flow for Kavach 2.0.

Manages the multi-turn detection conversation when a suspicious
transaction is intercepted. Implements a state machine:
IDLE -> TRANSACTION_DETECTED -> QUESTIONING -> CONFIRMED_SAFE / CONFIRMED_RISK
"""

from typing import Optional

from loguru import logger

from app.models.session import ConversationSession, SessionState
from app.models.transaction import Transaction, TransactionStatus, RiskLevel
from app.models.user import User
from app.agent.kavach_agent import kavach_agent, AgentResponse
from app.agent.risk_scorer import risk_scorer
from app.utils.language_utils import get_transaction_question


class DetectFlow:
    """
    Manages the multi-turn fraud detection conversation.

    State machine transitions:
    - IDLE -> TRANSACTION_DETECTED (when risky transaction found)
    - TRANSACTION_DETECTED -> QUESTIONING (first question sent)
    - QUESTIONING -> CONFIRMED_SAFE (user says no pressure)
    - QUESTIONING -> CONFIRMED_RISK (user confirms pressure)
    """

    async def initiate(
        self,
        transaction: Transaction,
        user: User,
        session: ConversationSession,
    ) -> AgentResponse:
        """
        Initiate detection flow when a risky transaction is intercepted.

        Scores the transaction, updates session state, and sends
        the first detection question to the user.

        Args:
            transaction: The intercepted transaction.
            user: User profile.
            session: Conversation session to use.

        Returns:
            AgentResponse with initial detection question.
        """
        # Score the transaction
        risk = risk_scorer.score_transaction(
            transaction=transaction,
            user=user,
            is_new_recipient=True,
            recent_call=False,
        )

        # Update transaction risk
        transaction.risk_score = risk.total_score
        transaction.risk_level = risk.risk_level.value
        transaction.status = TransactionStatus.FLAGGED

        # Update session
        session.state = SessionState.TRANSACTION_DETECTED
        session.transaction_id = transaction.id
        session.risk_score = risk.total_score
        session.risk_level = risk.risk_level.value

        # Get language-appropriate question
        language = user.language_preference
        question = get_transaction_question(language, transaction.amount)

        # Record in session
        session.add_message("system", f"Transaction intercepted: ₹{transaction.amount:,.0f}")
        session.add_message("agent", question)

        logger.info(
            f"DetectFlow initiated for {user.phone}: "
            f"₹{transaction.amount:,.0f}, risk={risk.total_score}/100 "
            f"({risk.risk_level.value})"
        )

        return AgentResponse(
            message=question,
            action="QUESTION",
            risk_level=risk.risk_level,
            risk_score=risk.total_score,
            should_alert_contact=(risk.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}),
            should_start_recovery=False,
        )

    async def process_response(
        self,
        message: str,
        session: ConversationSession,
        transaction: Optional[Transaction] = None,
        user: Optional[User] = None,
    ) -> AgentResponse:
        """
        Process user's response during an active detection flow.

        Delegates to KavachAgent for intelligent response handling.

        Args:
            message: User's reply message.
            session: Active conversation session.
            transaction: Associated transaction.
            user: User profile.

        Returns:
            AgentResponse with next action.
        """
        phone = user.phone if user else session.user_phone
        response = await kavach_agent.process_message(
            phone=phone,
            message=message,
            session=session,
            transaction=transaction,
            user=user,
        )

        logger.info(
            f"DetectFlow response for {phone}: "
            f"action={response.action}, risk={response.risk_level.value}"
        )

        return response

    def get_current_state(self, session: ConversationSession) -> SessionState:
        """
        Get the current state of the detection flow.

        Args:
            session: Current conversation session.

        Returns:
            Current SessionState.
        """
        return SessionState(session.state)

    def is_active(self, session: ConversationSession) -> bool:
        """
        Check if detection flow is currently active.

        Args:
            session: Conversation session.

        Returns:
            True if flow is in an active state.
        """
        active_states = {
            SessionState.TRANSACTION_DETECTED,
            SessionState.QUESTIONING,
        }
        return SessionState(session.state) in active_states


# Singleton instance
detect_flow = DetectFlow()
