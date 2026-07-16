"""
LLM client for Kavach 2.0.

Supports multiple backends:
- Google Gemini (FREE tier - default for demo)
- Anthropic Claude (paid - optional upgrade)

Provides async interface with retry logic, token usage logging,
and JSON response parsing.
"""

import json
import asyncio
from typing import Optional

import httpx
from loguru import logger

from app.config import settings


class ClaudeClient:
    """
    Unified LLM client with Gemini (free) and Claude (paid) support.

    Uses Gemini by default (free, no credit card needed).
    Falls back to Claude if ANTHROPIC_API_KEY is set and Gemini fails.
    """

    MAX_RETRIES = 3
    BASE_DELAY = 1.0

    def __init__(self) -> None:
        """Initialize LLM client — auto-selects best available backend."""
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        # Determine which backend to use
        self._use_gemini = bool(settings.GEMINI_API_KEY)
        self._use_claude = bool(settings.ANTHROPIC_API_KEY)

        if self._use_gemini:
            logger.info("LLM Backend: Google Gemini (free tier)")
        elif self._use_claude:
            logger.info("LLM Backend: Anthropic Claude")
        else:
            logger.warning(
                "No LLM API key configured (GEMINI_API_KEY or ANTHROPIC_API_KEY). "
                "Scam detection will use keyword fallback only."
            )

    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1000,
    ) -> str:
        """
        Send a completion request with retry logic.

        Tries Gemini first (free), then Claude if available.

        Args:
            system: System prompt.
            user: User message content.
            max_tokens: Maximum tokens in response.

        Returns:
            LLM text response.

        Raises:
            Exception: If all backends and retries fail.
        """
        if self._use_gemini:
            try:
                return await self._complete_gemini(system, user, max_tokens)
            except Exception as e:
                logger.warning(f"Gemini failed: {e}")
                if self._use_claude:
                    return await self._complete_claude(system, user, max_tokens)
                raise

        if self._use_claude:
            return await self._complete_claude(system, user, max_tokens)

        raise Exception("No LLM API key configured")

    async def _complete_gemini(
        self, system: str, user: str, max_tokens: int
    ) -> str:
        """Call Google Gemini API (free tier)."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash-lite:generateContent?key={settings.GEMINI_API_KEY}"
        )

        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.3,
            },
        }

        last_error: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    result = response.json()

                # Extract text
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")
                        # Log usage
                        usage = result.get("usageMetadata", {})
                        self._total_input_tokens += usage.get("promptTokenCount", 0)
                        self._total_output_tokens += usage.get("candidatesTokenCount", 0)
                        logger.debug(f"Gemini API call successful (attempt {attempt + 1})")
                        return text

                raise Exception("Empty response from Gemini")

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    delay = self.BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Gemini rate limit (attempt {attempt + 1}), retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Gemini API error: {e.response.status_code} - {e.response.text[:200]}")
                    break
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.BASE_DELAY * (2 ** attempt))
                else:
                    break

        raise last_error or Exception("Gemini API call failed")

    async def _complete_claude(
        self, system: str, user: str, max_tokens: int
    ) -> str:
        """Call Anthropic Claude API (paid)."""
        try:
            from anthropic import AsyncAnthropic, APIError, RateLimitError
        except ImportError:
            raise Exception("anthropic package not installed")

        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        last_error: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                text = response.content[0].text
                self._total_input_tokens += response.usage.input_tokens
                self._total_output_tokens += response.usage.output_tokens
                return text

            except RateLimitError as e:
                last_error = e
                await asyncio.sleep(self.BASE_DELAY * (2 ** attempt))
            except APIError as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.BASE_DELAY * (2 ** attempt))
                else:
                    break
            except Exception as e:
                last_error = e
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
            Parsed JSON dict from LLM response.
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
            logger.error(f"Failed to parse LLM JSON response: {e}\nRaw: {response_text[:200]}")
            raise

    def get_token_usage(self) -> dict[str, int]:
        """Return cumulative token usage stats."""
        return {
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
        }


# Singleton instance
claude_client = ClaudeClient()
