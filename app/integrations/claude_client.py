"""
LLM client for Kavach 2.0.

Supports: Groq (FREE, fast) > Gemini (FREE) > Claude (paid) > keyword fallback.
Uses Groq by default — 30 req/min free tier, <1 second responses.
"""

import json
import asyncio
from typing import Optional

import httpx
from loguru import logger

from app.config import settings


class ClaudeClient:
    """Unified LLM client. Tries Groq first (free, fast), then Gemini, then Claude."""

    MAX_RETRIES = 2
    BASE_DELAY = 1.0

    def __init__(self) -> None:
        self._use_groq = bool(settings.GROQ_API_KEY)
        self._use_gemini = bool(settings.GEMINI_API_KEY)
        self._use_claude = bool(settings.ANTHROPIC_API_KEY)

        if self._use_groq:
            logger.info("LLM Backend: Groq (free tier, fast)")
        elif self._use_gemini:
            logger.info("LLM Backend: Google Gemini (free tier)")
        elif self._use_claude:
            logger.info("LLM Backend: Anthropic Claude")
        else:
            logger.warning("No LLM API key configured. Using keyword fallback only.")

    async def complete(self, system: str, user: str, max_tokens: int = 1000) -> str:
        """Send completion request. Tries Groq > Gemini > Claude."""
        if self._use_groq:
            try:
                return await self._complete_groq(system, user, max_tokens)
            except Exception as e:
                logger.warning(f"Groq failed: {e}")

        if self._use_gemini:
            try:
                return await self._complete_gemini(system, user, max_tokens)
            except Exception as e:
                logger.warning(f"Gemini failed: {e}")

        if self._use_claude:
            try:
                return await self._complete_claude(system, user, max_tokens)
            except Exception as e:
                logger.warning(f"Claude failed: {e}")

        raise Exception("All LLM backends failed or not configured")

    async def _complete_groq(self, system: str, user: str, max_tokens: int) -> str:
        """Call Groq API (free, fast, reliable)."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            text = result["choices"][0]["message"]["content"]
            logger.debug(f"Groq response received ({len(text)} chars)")
            return text

    async def _complete_gemini(self, system: str, user: str, max_tokens: int) -> str:
        """Call Google Gemini API (free tier)."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash-lite:generateContent?key={settings.GEMINI_API_KEY}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        raise Exception("Empty Gemini response")

    async def _complete_claude(self, system: str, user: str, max_tokens: int) -> str:
        """Call Anthropic Claude API (paid)."""
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    async def complete_json(self, system: str, user: str, max_tokens: int = 1000) -> dict:
        """Send completion expecting JSON output."""
        response_text = await self.complete(
            system=system + "\n\nRespond with valid JSON only. No markdown.",
            user=user,
            max_tokens=max_tokens,
        )
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())

    def get_token_usage(self) -> dict[str, int]:
        return {"total_input_tokens": 0, "total_output_tokens": 0}


# Singleton
claude_client = ClaudeClient()
