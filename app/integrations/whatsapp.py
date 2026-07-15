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


BASE_URL = "https://graph.facebook.com/v25.0"


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

        Tries free-form text first. If user hasn't messaged within 24h,
        falls back to hello_world template (which can be sent anytime).

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

        # Try free-form text first
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
            error_code = e.response.status_code
            # If 400/403 — likely no 24h window, try template
            if error_code in (400, 403):
                logger.warning(
                    f"Free-text failed ({error_code}), trying template message"
                )
                return await self._send_as_template(to, message)
            logger.error(
                f"WhatsApp API error ({error_code}): {e.response.text}"
            )
            return False
        except httpx.RequestError as e:
            logger.error(f"WhatsApp request failed: {e}")
            return False

    async def _send_as_template(self, to: str, message: str) -> bool:
        """
        Send message using hello_world template as fallback.

        This works even without a 24-hour conversation window.
        After template delivery, user can reply and open free-text window.

        Args:
            to: Recipient phone number.
            message: Original message (logged for reference).

        Returns:
            True if template was sent successfully.
        """
        url = f"{BASE_URL}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to.lstrip("+"),
            "type": "template",
            "template": {
                "name": "hello_world",
                "language": {"code": "en_US"},
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url, json=payload, headers=self.headers
                )
                response.raise_for_status()
                logger.info(
                    f"WhatsApp template sent to {to} "
                    f"(original message logged: {message[:50]}...)"
                )
                return True
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(f"WhatsApp template also failed: {e}")
            return False

    async def send_buttons(
        self, to: str, body: str, buttons: list[dict[str, str]]
    ) -> bool:
        """
        Send interactive reply buttons (max 3). User taps instead of typing.

        Args:
            to: Recipient phone number.
            body: Message body text.
            buttons: List of {"id": "btn_1", "title": "Yes"} (max 3).

        Returns:
            True if sent successfully.
        """
        if not self._enabled:
            logger.info(f"[WhatsApp MOCK] Buttons to: {to} | {body} | {buttons}")
            return True

        url = f"{BASE_URL}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to.lstrip("+"),
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                        for b in buttons[:3]
                    ]
                },
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                logger.info(f"WhatsApp buttons sent to {to}")
                return True
        except httpx.HTTPStatusError as e:
            logger.warning(f"Buttons failed ({e.response.status_code}), sending as text")
            text = body + "\n\n" + "\n".join(f"{i+1}. {b['title']}" for i, b in enumerate(buttons))
            return await self.send_message(to, text)
        except httpx.RequestError as e:
            logger.error(f"WhatsApp buttons request failed: {e}")
            return False

    async def send_list(
        self, to: str, body: str, button_text: str, sections: list[dict]
    ) -> bool:
        """
        Send interactive list message. User taps to open menu and selects.

        Args:
            to: Recipient phone number.
            body: Message body text.
            button_text: Text on the list button (e.g. "Select option").
            sections: List of sections with rows.

        Returns:
            True if sent successfully.
        """
        if not self._enabled:
            logger.info(f"[WhatsApp MOCK] List to: {to} | {body}")
            return True

        url = f"{BASE_URL}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to.lstrip("+"),
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body},
                "action": {
                    "button": button_text,
                    "sections": sections,
                },
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                logger.info(f"WhatsApp list sent to {to}")
                return True
        except httpx.HTTPStatusError as e:
            logger.warning(f"List failed ({e.response.status_code}), sending as text")
            text = body + "\n\n"
            for section in sections:
                for row in section.get("rows", []):
                    text += f"- {row['title']}\n"
            return await self.send_message(to, text)
        except httpx.RequestError as e:
            logger.error(f"WhatsApp list request failed: {e}")
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
