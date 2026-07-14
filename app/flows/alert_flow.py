"""
Alert flow for Kavach 2.0.

Handles alerting the user's trusted contact when fraud is detected.
Sends via WhatsApp first, falls back to SMS via Twilio.
Respects privacy by never sharing exact conversation content.
"""

from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from app.models.user import User
from app.models.transaction import Transaction
from app.agent.scam_detector import DetectionResult
from app.integrations.whatsapp import whatsapp_client
from app.integrations.twilio_sms import twilio_client


class AlertFlow:
    """
    Manages alerting trusted contacts when fraud is detected.

    Sends alerts via WhatsApp with SMS fallback. Never shares
    exact conversation content with the trusted contact.
    """

    async def send_trusted_alert(
        self,
        user: User,
        transaction: Transaction,
        risk: DetectionResult,
    ) -> bool:
        """
        Send alert to user's trusted contact about potential fraud.

        Alert message (in English):
        "[USER_NAME] is about to transfer ₹[AMOUNT] to an unknown account
        and may be under pressure from a scammer. Please call them
        immediately. - Kavach 2.0"

        Args:
            user: User whose trusted contact should be alerted.
            transaction: The flagged transaction.
            risk: Detection result with risk details.

        Returns:
            True if alert was delivered successfully via any channel.
        """
        if not user.trusted_contact_phone:
            logger.warning(
                f"No trusted contact configured for user {user.phone}"
            )
            return False

        # Build alert message (English for trusted contact)
        user_name = user.name or "Your contact"
        amount = f"₹{transaction.amount:,.0f}"
        alert_message = (
            f"🚨 *Kavach 2.0 Alert*\n\n"
            f"{user_name} is about to transfer {amount} to an unknown account "
            f"and may be under pressure from a scammer.\n\n"
            f"⚠️ Risk Level: {risk.risk_level.value}\n\n"
            f"Please call them immediately at {user.phone}.\n\n"
            f"— Kavach 2.0 Trusted Circle Agent"
        )

        # Try WhatsApp first
        whatsapp_sent = await whatsapp_client.send_message(
            to=user.trusted_contact_phone,
            message=alert_message,
        )

        if whatsapp_sent:
            logger.info(
                f"Alert sent via WhatsApp to trusted contact "
                f"{user.trusted_contact_phone} for user {user.phone}"
            )
            self._log_alert(user, transaction, "whatsapp", True)
            return True

        # Fallback to SMS
        logger.warning(
            f"WhatsApp alert failed, falling back to SMS for "
            f"{user.trusted_contact_phone}"
        )
        sms_message = (
            f"[Kavach Alert] {user_name} is about to transfer {amount} "
            f"to an unknown account and may be under scammer pressure. "
            f"Please call them NOW at {user.phone}. - Kavach 2.0"
        )
        sms_sent = await twilio_client.send_sms(
            to=user.trusted_contact_phone,
            message=sms_message,
        )

        if sms_sent:
            logger.info(
                f"Alert sent via SMS to trusted contact "
                f"{user.trusted_contact_phone} for user {user.phone}"
            )
            self._log_alert(user, transaction, "sms", True)
            return True

        logger.error(
            f"Failed to send alert via both WhatsApp and SMS to "
            f"{user.trusted_contact_phone}"
        )
        self._log_alert(user, transaction, "none", False)
        return False

    async def send_fraud_confirmed_alert(
        self,
        user: User,
        transaction: Transaction,
    ) -> bool:
        """
        Notify trusted contact that fraud was confirmed and user is being guided.

        Args:
            user: User profile.
            transaction: The flagged transaction.

        Returns:
            True if notification was sent successfully.
        """
        if not user.trusted_contact_phone:
            return False

        user_name = user.name or "Your contact"
        message = (
            f"✅ *Kavach 2.0 Update*\n\n"
            f"The fraud attempt on {user_name} has been confirmed and blocked. "
            f"Kavach is now guiding them through recovery steps "
            f"(filing complaint, contacting bank, calling 1930 helpline).\n\n"
            f"Please check on them when you can.\n\n"
            f"— Kavach 2.0"
        )

        sent = await whatsapp_client.send_message(
            to=user.trusted_contact_phone,
            message=message,
        )

        if not sent:
            # SMS fallback
            sms_msg = (
                f"[Kavach Update] Fraud on {user_name} confirmed & blocked. "
                f"Recovery guidance in progress. Please check on them. - Kavach 2.0"
            )
            sent = await twilio_client.send_sms(
                to=user.trusted_contact_phone,
                message=sms_msg,
            )

        return sent

    def _log_alert(
        self,
        user: User,
        transaction: Transaction,
        channel: str,
        success: bool,
    ) -> None:
        """
        Log alert delivery details.

        Args:
            user: User whose contact was alerted.
            transaction: Related transaction.
            channel: Delivery channel used (whatsapp/sms/none).
            success: Whether delivery succeeded.
        """
        logger.info(
            f"[ALERT LOG] user={user.phone}, "
            f"trusted_contact={user.trusted_contact_phone}, "
            f"channel={channel}, success={success}, "
            f"amount=₹{transaction.amount:,.0f}, "
            f"timestamp={datetime.now(timezone.utc).isoformat()}"
        )


# Singleton instance
alert_flow = AlertFlow()
