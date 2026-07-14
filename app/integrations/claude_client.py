"""
Claude API client for Kavach 2.0.

Provides async interface to Anthropic's Claude claude-sonnet-4-6 model
with retry logic, token usage logging, and JSON response parsing.
"""

import json
import asyncio
from typing import Optional

from anthropic import AsyncAnthropic, APIError, RateLimitError
from loguru import logger

from app.config import settings


class ClaudeClient:
    """Async client for Anthropic Claude API with retry and structured output."""

    MODEL = "claude-sonnet-4-6"
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds

    def __init__(self) -> None:
        """Initialize Claude client with API key from settings."""
        self._client: Optional[AsyncAnthropic] = None
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    @property
    def client(self) -> AsyncAnthropic:
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            if not settings.ANTHROPIC_API_KEY:
                logger.warning("ANTHROPIC_API_KEY not set — Claude calls will fail")
            self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1000,
    ) -> str:
        """
        Send a completion request to Claude with retry logic.

        Args:
            system: System prompt guiding Claude's behavior.
            user: User message content.
            max_tokens: Maximum tokens in response.

        Returns:
            Claude's text response.

        Raises:
            APIError: If all retries are exhausted.
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self.client.messages.create(
                    model=self.MODEL,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )

                # Log token usage
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                self._total_input_tokens += input_tokens
                self._total_output_tokens += output_tokens
                logger.debug(
                    f"Claude API call: {input_tokens} input, {output_tokens} output tokens "
                    f"(total: {self._total_input_tokens}/{self._total_output_tokens})"
                )

                # Extract text content
                text = response.content[0].text
                return text

            except RateLimitError as e:
                last_error = e
                delay = self.BASE_DELAY * (2 ** attempt)
                logger.warning(
                    f"Claude rate limit hit (attempt {attempt + 1}/{self.MAX_RETRIES}), "
                    f"retrying in {delay}s"
                )
                await asyncio.sleep(delay)

            except APIError as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        f"Claude API error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}, "
                        f"retrying in {delay}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Claude API failed after {self.MAX_RETRIES} attempts: {e}")

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error calling Claude: {e}")
                break

        raise last_error or Exception("Claude API call failed")

    async def complete_json(
        self,
        system: str,
        user: str,
        max_tokens: int = 1000,
    ) -> dict:
        """
        Send a completion request expecting JSON-structured output.

        Args:
            system: System prompt (should instruct JSON output).
            user: User message content.
            max_tokens: Maximum tokens in response.

        Returns:
            Parsed JSON dict from Claude's response.

        Raises:
            json.JSONDecodeError: If response is not valid JSON.
        """
        response_text = await self.complete(
            system=system + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation.",
            user=user,
            max_tokens=max_tokens,
        )

        # Strip markdown code fences if present
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude JSON response: {e}\nRaw: {response_text[:200]}")
            raise

    def get_token_usage(self) -> dict[str, int]:
        """Return cumulative token usage stats."""
        return {
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
        }


# Singleton instance
claude_client = ClaudeClient()
