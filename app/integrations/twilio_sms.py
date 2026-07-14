"""
Twilio SMS client for Kavach 2.0.

Provides SMS fallback when WhatsApp delivery fails.
Used primarily for alerting trusted contacts.
"""

from typing import Optional

import httpx
from loguru import logger

from app.config import settings


class TwilioClient:
    """Async client for Twilio SMS API."""

    BASE_URL = "https://api.twilio.com/2010-04-01"

    def __init__(self) -> None:
        """Initialize with Twilio credentials from settings."""
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_PHONE_NUMBER
        self._enabled = bool(
            self.account_sid and self.auth_token and self.from_number
        )

        if not self._enabled:
            logger.warning(
                "Twilio credentials not configured — SMS will be logged only"
            )

    async def send_sms(self, to: str, message: str) -> bool:
        """
        Send an SMS message via Twilio.

        Args:
            to: Recipient phone number in E.164 format.
            message: SMS text content (max 1600 chars).

        Returns:
            True if message was sent/queued successfully, False otherwise.
        """
        if not self._enabled:
            logger.info(f"[Twilio MOCK] SMS to: {to} | Message: {message}")
            return True

        url = f"{self.BASE_URL}/Accounts/{self.account_sid}/Messages.json"

        # Truncate message to SMS limit
        if len(message) > 1600:
            message = message[:1597] + "..."
            logger.warning("SMS message truncated to 1600 characters")

        payload = {
            "To": to,
            "From": self.from_number,
            "Body": message,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    data=payload,
                    auth=(self.account_sid, self.auth_token),
                )
                response.raise_for_status()

                result = response.json()
                sid = result.get("sid", "unknown")
                status = result.get("status", "unknown")
                logger.info(
                    f"Twilio SMS sent to {to} (SID: {sid}, status: {status})"
                )
                return True

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Twilio API error ({e.response.status_code}): "
                f"{e.response.text}"
            )
            return False
        except httpx.RequestError as e:
            logger.error(f"Twilio request failed: {e}")
            return False


# Singleton instance
twilio_client = TwilioClient()
