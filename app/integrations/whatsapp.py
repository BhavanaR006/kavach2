"""
WhatsApp Business Cloud API client for Kavach 2.0.

Handles sending messages, template messages, and parsing
incoming webhook payloads from Meta's WhatsApp API v18.0.
"""

from dataclasses import dataclass
from typing import Optional

import httpx
from loguru import logger

from app.config import settings


BASE_URL = "https://graph.facebook.com/v18.0"


@dataclass
class WhatsAppMessage:
    """Parsed incoming WhatsApp message."""
    from_number: str
    message_id: str
    text: str
    timestamp: str
    message_type: str = "text"


class WhatsAppClient:
    """Client for Meta WhatsApp Business Cloud API v18.0."""

    def __init__(self) -> None:
        """Initialize with WhatsApp credentials from settings."""
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self._enabled = bool(self.access_token and self.phone_number_id)

        if not self._enabled:
            logger.warning(
                "WhatsApp credentials not configured — messages will be logged only"
            )

    @property
    def headers(self) -> dict[str, str]:
        """Authorization headers for Meta API."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def send_message(self, to: str, message: str) -> bool:
        """
        Send a text message via WhatsApp.

        Args:
            to: Recipient phone number in E.164 format.
            message: Text message content.

        Returns:
            True if message was sent successfully, False otherwise.
        """
        if not self._enabled:
            logger.info(f"[WhatsApp MOCK] To: {to} | Message: {message}")
            return True

        url = f"{BASE_URL}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to.lstrip("+"),
            "type": "text",
            "text": {"body": message},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url, json=payload, headers=self.headers
                )
                response.raise_for_status()
                logger.info(f"WhatsApp message sent to {to}")
                return True

        except httpx.HTTPStatusError as e:
            logger.error(
                f"WhatsApp API error ({e.response.status_code}): "
                f"{e.response.text}"
            )
            return False
        except httpx.RequestError as e:
            logger.error(f"WhatsApp request failed: {e}")
            return False

    async def send_template_message(
        self,
        to: str,
        template: str,
        params: Optional[dict] = None,
    ) -> bool:
        """
        Send a template message via WhatsApp.

        Args:
            to: Recipient phone number in E.164 format.
            template: Template name registered with Meta.
            params: Template parameter values.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not self._enabled:
            logger.info(
                f"[WhatsApp MOCK] Template to: {to} | Template: {template} | Params: {params}"
            )
            return True

        url = f"{BASE_URL}/{self.phone_number_id}/messages"

        components = []
        if params:
            parameters = [
                {"type": "text", "text": str(v)} for v in params.values()
            ]
            components.append(
                {"type": "body", "parameters": parameters}
            )

        payload = {
            "messaging_product": "whatsapp",
            "to": to.lstrip("+"),
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": "en"},
                "components": components,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url, json=payload, headers=self.headers
                )
                response.raise_for_status()
                logger.info(f"WhatsApp template '{template}' sent to {to}")
                return True

        except httpx.HTTPStatusError as e:
            logger.error(
                f"WhatsApp template API error ({e.response.status_code}): "
                f"{e.response.text}"
            )
            return False
        except httpx.RequestError as e:
            logger.error(f"WhatsApp template request failed: {e}")
            return False

    @staticmethod
    def parse_webhook(payload: dict) -> Optional[WhatsAppMessage]:
        """
        Parse incoming WhatsApp webhook payload into a WhatsAppMessage.

        Args:
            payload: Raw webhook JSON payload from Meta.

        Returns:
            WhatsAppMessage if a text message is found, None otherwise.
        """
        try:
            entry = payload.get("entry", [])
            if not entry:
                return None

            changes = entry[0].get("changes", [])
            if not changes:
                return None

            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            if not messages:
                return None

            msg = messages[0]
            msg_type = msg.get("type", "text")

            # Extract text content
            text = ""
            if msg_type == "text":
                text = msg.get("text", {}).get("body", "")
            elif msg_type == "interactive":
                interactive = msg.get("interactive", {})
                if "button_reply" in interactive:
                    text = interactive["button_reply"].get("title", "")
                elif "list_reply" in interactive:
                    text = interactive["list_reply"].get("title", "")

            return WhatsAppMessage(
                from_number=msg.get("from", ""),
                message_id=msg.get("id", ""),
                text=text,
                timestamp=msg.get("timestamp", ""),
                message_type=msg_type,
            )

        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to parse WhatsApp webhook: {e}")
            return None


# Singleton instance
whatsapp_client = WhatsAppClient()
