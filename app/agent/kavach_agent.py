"""
Main orchestrator agent for Kavach 2.0.

Implements the PERCEIVE -> REASON -> ACT -> LEARN agentic loop
for fraud detection and user protection.
"""

from dataclasses import dataclass
from typing import Optional

from loguru import logger

from app.models.session import ConversationSession, SessionState
from app.models.transaction import Transaction, RiskLevel
from app.models.user import User
from app.agent.scam_detector import scam_detector, DetectionResult
from app.agent.risk_scorer import risk_scorer, TransactionRisk
from app.utils.language_utils import (
    get_transaction_question,
    get_followup_question,
    is_affirmative,
    is_negative,
    detect_script,
)


@dataclass
class AgentResponse:
    """Response from the Kavach agent."""
    message: str
    action: str  # CONTINUE, QUESTION, ALERT, RECOVERY, SAFE
    risk_level: RiskLevel
    risk_score: int = 0
    should_alert_contact: bool = False
    should_start_recovery: bool = False


class KavachAgent:
    """
    Main orchestrator implementing PERCEIVE -> REASON -> ACT -> LEARN.

    Manages the fraud detection conversation flow and coordinates
    between scam detector, risk scorer, and recovery systems.
    """

    async def process_message(
        self,
        phone: str,
        message: str,
        session: ConversationSession,
        transaction: Optional[Transaction] = None,
        user: Optional[User] = None,
    ) -> AgentResponse:
        """
        Process an incoming user message through the agentic loop.

        Args:
            phone: User's phone number.
            message: Incoming message text.
            session: Current conversation session.
            transaction: Associated transaction (if any).
            user: User profile.

        Returns:
            AgentResponse with message, action, and risk assessment.
        """
        language = user.language_preference if user else detect_script(message)

        # Record the incoming message
        session.add_message("user", message)

        # PERCEIVE: Gather context
        context = self._perceive(session, transaction)

        # REASON: Analyze for scam signals
        detection = await self._reason(message, context, language)

        # ACT: Take appropriate action based on risk + session state
        response = await self._act(
            detection, session, transaction, user, message, language
        )

        # LEARN: Log pattern for future reference
        self._learn(detection, session)

        # Record agent response
        session.add_message("agent", response.message)

        return response

    def _perceive(
        self,
        session: ConversationSession,
        transaction: Optional[Transaction],
    ) -> dict:
        """
        PERCEIVE phase: gather all available context.

        Args:
            session: Current conversation session.
            transaction: Associated transaction if any.

        Returns:
            Context dictionary for analysis.
        """
        context = {
            "session_state": session.state,
            "message_count": session.get_message_count(),
            "previous_risk_score": session.risk_score,
        }

        if transaction:
            context["transaction"] = {
                "amount": transaction.amount,
                "recipient": transaction.recipient_phone,
                "status": transaction.status,
            }

        # Include recent conversation history for context
        if session.messages:
            recent = session.messages[-5:]  # Last 5 messages
            context["recent_messages"] = [
                {"role": m["role"], "content": m["content"]}
                for m in recent
            ]

        return context

    async def _reason(
        self,
        message: str,
        context: dict,
        language: str,
    ) -> DetectionResult:
        """
        REASON phase: analyze message for scam signals.

        Args:
            message: Current user message.
            context: Gathered context.
            language: Detected language.

        Returns:
            DetectionResult with risk assessment.
        """
        detection = await scam_detector.detect(
            message=message,
            context=context,
            language=language,
        )

        logger.info(
            f"Detection result: score={detection.risk_score}, "
            f"level={detection.risk_level}, signals={detection.signals}"
        )

        return detection

    async def _act(
        self,
        detection: DetectionResult,
        session: ConversationSession,
        transaction: Optional[Transaction],
        user: Optional[User],
        message: str,
        language: str,
    ) -> AgentResponse:
        """
        ACT phase: take appropriate action based on risk and state.

        Actions by risk level:
        - LOW: Continue normal conversation
        - MEDIUM: Ask follow-up clarifying question
        - HIGH: Send trusted contact alert + pause guidance
        - CRITICAL: Immediate alert + full recovery flow

        Args:
            detection: Scam detection result.
            session: Current session.
            transaction: Associated transaction.
            user: User profile.
            message: Current message.
            language: User's language.

        Returns:
            AgentResponse with appropriate action.
        """
        # Handle responses to our questions (state-based)
        if session.state == SessionState.QUESTIONING:
            return self._handle_questioning_response(
                message, detection, session, language
            )

        # Handle based on current state
        if session.state == SessionState.TRANSACTION_DETECTED:
            return self._handle_transaction_detected(
                detection, session, language, transaction
            )

        # Default: act based on detection risk level
        if detection.risk_level == RiskLevel.CRITICAL:
            session.state = SessionState.CONFIRMED_RISK
            session.risk_score = detection.risk_score
            session.risk_level = detection.risk_level.value
            return AgentResponse(
                message=self._get_critical_message(language),
                action="RECOVERY",
                risk_level=RiskLevel.CRITICAL,
                risk_score=detection.risk_score,
                should_alert_contact=True,
                should_start_recovery=True,
            )

        if detection.risk_level == RiskLevel.HIGH:
            session.state = SessionState.QUESTIONING
            session.risk_score = detection.risk_score
            session.risk_level = detection.risk_level.value
            return AgentResponse(
                message=get_followup_question(language),
                action="QUESTION",
                risk_level=RiskLevel.HIGH,
                risk_score=detection.risk_score,
                should_alert_contact=True,
                should_start_recovery=False,
            )

        if detection.risk_level == RiskLevel.MEDIUM:
            session.state = SessionState.QUESTIONING
            session.risk_score = detection.risk_score
            return AgentResponse(
                message=get_followup_question(language),
                action="QUESTION",
                risk_level=RiskLevel.MEDIUM,
                risk_score=detection.risk_score,
                should_alert_contact=False,
                should_start_recovery=False,
            )

        # LOW risk
        session.risk_score = detection.risk_score
        return AgentResponse(
            message=self._get_safe_message(language),
            action="CONTINUE",
            risk_level=RiskLevel.LOW,
            risk_score=detection.risk_score,
            should_alert_contact=False,
            should_start_recovery=False,
        )

    def _handle_questioning_response(
        self,
        message: str,
        detection: DetectionResult,
        session: ConversationSession,
        language: str,
    ) -> AgentResponse:
        """
        Handle user's response during QUESTIONING state.

        Args:
            message: User's reply (yes/no/other).
            detection: Detection result for context.
            session: Current session.
            language: User's language.

        Returns:
            AgentResponse based on user confirmation.
        """
        if is_affirmative(message):
            # User confirms they are being pressured
            session.state = SessionState.CONFIRMED_RISK
            session.risk_score = max(session.risk_score, 80)
            session.risk_level = RiskLevel.CRITICAL.value
            return AgentResponse(
                message=self._get_critical_message(language),
                action="RECOVERY",
                risk_level=RiskLevel.CRITICAL,
                risk_score=session.risk_score,
                should_alert_contact=True,
                should_start_recovery=True,
            )

        if is_negative(message):
            # User says they are not being pressured
            session.state = SessionState.CONFIRMED_SAFE
            return AgentResponse(
                message=self._get_safe_message(language),
                action="SAFE",
                risk_level=RiskLevel.LOW,
                risk_score=0,
                should_alert_contact=False,
                should_start_recovery=False,
            )

        # Ambiguous response — ask again more specifically
        return AgentResponse(
            message=get_followup_question(language),
            action="QUESTION",
            risk_level=detection.risk_level,
            risk_score=detection.risk_score,
            should_alert_contact=False,
            should_start_recovery=False,
        )

    def _handle_transaction_detected(
        self,
        detection: DetectionResult,
        session: ConversationSession,
        language: str,
        transaction: Optional[Transaction],
    ) -> AgentResponse:
        """
        Handle initial transaction detection state.

        Args:
            detection: Detection result.
            session: Current session.
            language: User's language.
            transaction: The detected transaction.

        Returns:
            AgentResponse with transaction question.
        """
        amount = transaction.amount if transaction else 0
        session.state = SessionState.QUESTIONING
        return AgentResponse(
            message=get_transaction_question(language, amount),
            action="QUESTION",
            risk_level=detection.risk_level,
            risk_score=detection.risk_score,
            should_alert_contact=False,
            should_start_recovery=False,
        )

    def _learn(self, detection: DetectionResult, session: ConversationSession) -> None:
        """
        LEARN phase: log patterns for future improvement.

        Args:
            detection: Detection result to log.
            session: Current session for context.
        """
        if detection.risk_score > 50:
            logger.info(
                f"[LEARN] High-risk pattern detected: "
                f"signals={detection.signals}, score={detection.risk_score}"
            )

    @staticmethod
    def _get_critical_message(language: str) -> str:
        """Get critical risk alert message in user's language."""
        messages = {
            "hi": (
                "🚨 *खतरा!* यह एक scam हो सकता है!\n\n"
                "आपको जो भी call/message आया है, वो fraud है। "
                "कोई भी सरकारी agency इस तरह से payment नहीं मांगती।\n\n"
                "❌ कोई पैसा transfer न करें\n"
                "📞 हम आपके trusted contact को alert कर रहे हैं\n"
                "👇 Recovery steps नीचे दिए जा रहे हैं"
            ),
            "te": (
                "🚨 *ప్రమాదం!* ఇది ఒక scam కావచ్చు!\n\n"
                "మీకు వచ్చిన call/message మోసం. "
                "ఏ ప్రభుత్వ agency ఇలా payment అడగదు.\n\n"
                "❌ ఎలాంటి డబ్బు transfer చేయకండి\n"
                "📞 మీ trusted contact కు alert పంపుతున్నాము\n"
                "👇 Recovery steps క్రింద ఇవ్వబడుతున్నాయి"
            ),
            "ta": (
                "🚨 *ஆபத்து!* இது ஒரு scam ஆக இருக்கலாம்!\n\n"
                "உங்களுக்கு வந்த call/message மோசடி. "
                "எந்த அரசு agency இப்படி payment கேட்காது.\n\n"
                "❌ எந்த பணமும் transfer செய்யாதீர்கள்\n"
                "📞 உங்கள் trusted contact க்கு alert அனுப்புகிறோம்\n"
                "👇 Recovery steps கீழே கொடுக்கப்படுகின்றன"
            ),
            "bn": (
                "🚨 *বিপদ!* এটি একটি scam হতে পারে!\n\n"
                "আপনি যে call/message পেয়েছেন, সেটা প্রতারণা। "
                "কোনো সরকারি agency এভাবে payment চায় না।\n\n"
                "❌ কোনো টাকা transfer করবেন না\n"
                "📞 আপনার trusted contact কে alert পাঠাচ্ছি\n"
                "👇 Recovery steps নিচে দেওয়া হচ্ছে"
            ),
            "en": (
                "🚨 *DANGER!* This appears to be a scam!\n\n"
                "The call/message you received is fraudulent. "
                "No government agency asks for payment this way.\n\n"
                "❌ Do NOT transfer any money\n"
                "📞 We are alerting your trusted contact\n"
                "👇 Recovery steps are being sent below"
            ),
        }
        return messages.get(language, messages["en"])

    @staticmethod
    def _get_safe_message(language: str) -> str:
        """Get safe/all-clear message in user's language."""
        messages = {
            "hi": (
                "✅ ठीक है! आपकी transaction safe लगती है।\n\n"
                "अगर भविष्य में कोई suspicious call/message आए, "
                "तो Kavach से बात करें। हम हमेशा आपकी मदद के लिए यहाँ हैं। 🛡️"
            ),
            "te": (
                "✅ బాగుంది! మీ transaction సురక్షితంగా కనిపిస్తోంది.\n\n"
                "భవిష్యత్తులో ఏదైనా suspicious call/message వస్తే, "
                "Kavach తో మాట్లాడండి. మేము ఎల్లప్పుడూ మీకు సహాయం చేయడానికి ఉన్నాము. 🛡️"
            ),
            "ta": (
                "✅ சரி! உங்கள் transaction பாதுகாப்பாக தெரிகிறது.\n\n"
                "எதிர்காலத்தில் ஏதேனும் suspicious call/message வந்தால், "
                "Kavach உடன் பேசுங்கள். நாங்கள் எப்போதும் உங்களுக்கு உதவ இங்கே இருக்கிறோம். 🛡️"
            ),
            "bn": (
                "✅ ঠিক আছে! আপনার transaction নিরাপদ মনে হচ্ছে।\n\n"
                "ভবিষ্যতে কোনো suspicious call/message এলে, "
                "Kavach এর সাথে কথা বলুন। আমরা সবসময় আপনার সাহায্যের জন্য এখানে আছি। 🛡️"
            ),
            "en": (
                "✅ All good! Your transaction appears safe.\n\n"
                "If you receive any suspicious call/message in the future, "
                "talk to Kavach. We're always here to help. 🛡️"
            ),
        }
        return messages.get(language, messages["en"])


# Singleton instance
kavach_agent = KavachAgent()
