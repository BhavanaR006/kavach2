"""
Recovery flow for Kavach 2.0.

Full recovery orchestration after fraud is confirmed.
Delivers calming message, recovery guide, complaint template,
helpline info, and notifies trusted contact.
"""

from typing import Optional

from loguru import logger

from app.models.session import ConversationSession, SessionState
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User
from app.agent.recovery_agent import recovery_agent
from app.flows.alert_flow import alert_flow
from app.integrations.whatsapp import whatsapp_client


class RecoveryFlow:
    """
    Full recovery orchestration after fraud is confirmed.

    Steps:
    1. Send immediate calming message to user
    2. Send recovery guide in user's language
    3. Generate and send pre-filled complaint text
    4. Send 1930 helpline info
    5. Notify trusted contact that fraud confirmed
    6. Log full incident to database
    """

    async def execute(
        self,
        session: ConversationSession,
        user: User,
        transaction: Transaction,
    ) -> list[str]:
        """
        Execute the full recovery flow.

        Args:
            session: Active conversation session.
            user: User profile.
            transaction: The blocked transaction.

        Returns:
            List of messages sent to the user during recovery.
        """
        language = user.language_preference
        messages_sent: list[str] = []

        logger.info(
            f"Starting recovery flow for {user.phone}, "
            f"transaction ₹{transaction.amount:,.0f}"
        )

        # Update states
        session.state = SessionState.RECOVERY_IN_PROGRESS
        transaction.status = TransactionStatus.BLOCKED

        # Step 1: Calming message
        calming = await recovery_agent.get_calming_message(language)
        await self._send_to_user(user.phone, calming)
        messages_sent.append(calming)
        session.add_message("agent", calming)

        # Step 2: Recovery guide
        steps = await recovery_agent.get_recovery_guide(language)
        guide_header = self._get_guide_header(language)
        guide_message = guide_header + "\n\n" + "\n".join(
            f"{i}. {step}" for i, step in enumerate(steps, 1)
        )
        await self._send_to_user(user.phone, guide_message)
        messages_sent.append(guide_message)
        session.add_message("agent", guide_message)

        # Step 3: Complaint template
        complaint = await recovery_agent.generate_complaint_text(
            session, user, transaction
        )
        complaint_intro = self._get_complaint_intro(language)
        complaint_message = f"{complaint_intro}\n\n{complaint}"
        await self._send_to_user(user.phone, complaint_message)
        messages_sent.append(complaint_message)
        session.add_message("agent", "[Complaint template sent]")

        # Step 4: Helpline info
        helpline = await recovery_agent.get_helpline_message(language)
        await self._send_to_user(user.phone, helpline)
        messages_sent.append(helpline)
        session.add_message("agent", helpline)

        # Step 5: Notify trusted contact
        await alert_flow.send_fraud_confirmed_alert(user, transaction)

        # Step 6: Mark session as resolved
        session.state = SessionState.RESOLVED
        session.add_message(
            "system", "Recovery flow completed. Incident logged."
        )

        logger.info(
            f"Recovery flow completed for {user.phone}. "
            f"{len(messages_sent)} messages sent."
        )

        return messages_sent

    async def _send_to_user(self, phone: str, message: str) -> bool:
        """
        Send a message to the user via WhatsApp.

        Args:
            phone: User's phone number.
            message: Message content.

        Returns:
            True if sent successfully.
        """
        return await whatsapp_client.send_message(to=phone, message=message)

    @staticmethod
    def _get_guide_header(language: str) -> str:
        """Get recovery guide header in user's language."""
        headers = {
            "hi": "📋 *Recovery Steps — अभी ये करें:*",
            "te": "📋 *Recovery Steps — ఇప్పుడు ఇవి చేయండి:*",
            "ta": "📋 *Recovery Steps — இப்போது இவற்றைச் செய்யுங்கள்:*",
            "bn": "📋 *Recovery Steps — এখন এগুলো করুন:*",
            "en": "📋 *Recovery Steps — Do these now:*",
        }
        return headers.get(language, headers["en"])

    @staticmethod
    def _get_complaint_intro(language: str) -> str:
        """Get complaint template intro in user's language."""
        intros = {
            "hi": (
                "📄 *Cybercrime Complaint Template*\n"
                "नीचे दिया गया template cybercrime.gov.in पर submit करें:"
            ),
            "te": (
                "📄 *Cybercrime Complaint Template*\n"
                "క్రింద ఇచ్చిన template ను cybercrime.gov.in లో submit చేయండి:"
            ),
            "ta": (
                "📄 *Cybercrime Complaint Template*\n"
                "கீழே உள்ள template ஐ cybercrime.gov.in இல் submit செய்யுங்கள்:"
            ),
            "bn": (
                "📄 *Cybercrime Complaint Template*\n"
                "নিচের template টি cybercrime.gov.in এ submit করুন:"
            ),
            "en": (
                "📄 *Cybercrime Complaint Template*\n"
                "Submit the template below at cybercrime.gov.in:"
            ),
        }
        return intros.get(language, intros["en"])


# Singleton instance
recovery_flow = RecoveryFlow()
