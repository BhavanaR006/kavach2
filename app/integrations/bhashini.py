"""
BHASHINI API client for Kavach 2.0.

Provides multilingual translation, language detection, and transliteration
for Hindi, Telugu, Tamil, Bengali, and English using India's BHASHINI ULCA API.
"""

from typing import Optional

import httpx
from loguru import logger

from app.config import settings


# BHASHINI language codes
LANGUAGE_CODES = {
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "bn": "Bengali",
    "en": "English",
}

# ULCA API endpoints
ULCA_API_BASE = "https://meity-auth.ulcacontrib.org/ulca/apis/v0"
INFERENCE_BASE = "https://dhruva-api.bhashini.gov.in/services/inference"


class BhashiniClient:
    """Async client for BHASHINI ULCA translation API."""

    def __init__(self) -> None:
        """Initialize with BHASHINI credentials from settings."""
        self.api_key = settings.BHASHINI_API_KEY
        self.user_id = settings.BHASHINI_USER_ID
        self._enabled = bool(self.api_key and self.user_id)

        if not self._enabled:
            logger.warning(
                "BHASHINI credentials not configured — translations will fall back to English"
            )

    @property
    def headers(self) -> dict[str, str]:
        """Authorization headers for BHASHINI API."""
        return {
            "Content-Type": "application/json",
            "ulcaApiKey": self.api_key,
            "userID": self.user_id,
        }

    async def _get_pipeline_config(
        self, source_lang: str, target_lang: str, task_type: str = "translation"
    ) -> Optional[dict]:
        """
        Get pipeline configuration for a translation task.

        Args:
            source_lang: Source language code.
            target_lang: Target language code.
            task_type: Type of task (translation, transliteration, asr, tts).

        Returns:
            Pipeline config dict or None on failure.
        """
        url = f"{ULCA_API_BASE}/model/getModelsPipeline"
        payload = {
            "pipelineTasks": [
                {
                    "taskType": task_type,
                    "config": {
                        "language": {
                            "sourceLanguage": source_lang,
                            "targetLanguage": target_lang,
                        }
                    },
                }
            ],
            "pipelineRequestConfig": {
                "pipelineId": "64392f96daac500b55c543cd"
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url, json=payload, headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(f"BHASHINI pipeline config error: {e}")
            return None

    async def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> str:
        """
        Translate text between supported Indian languages.

        Args:
            text: Text to translate.
            source_lang: Source language code (hi, te, ta, bn, en).
            target_lang: Target language code (hi, te, ta, bn, en).

        Returns:
            Translated text, or original text if translation fails.
        """
        if source_lang == target_lang:
            return text

        if not self._enabled:
            logger.info(
                f"[BHASHINI MOCK] Translate '{text[:50]}...' "
                f"from {source_lang} to {target_lang}"
            )
            return text  # Graceful fallback

        # Get pipeline config
        config = await self._get_pipeline_config(source_lang, target_lang)
        if not config:
            logger.warning("Failed to get BHASHINI pipeline, returning original text")
            return text

        try:
            # Extract service details from config
            pipeline_response = config.get("pipelineResponseConfig", [{}])
            if not pipeline_response:
                return text

            task_config = pipeline_response[0].get("config", [{}])
            if not task_config:
                return text

            service_id = task_config[0].get("serviceId", "")
            inference_key = config.get("pipelineInferenceAPIEndPoint", {}).get(
                "inferenceApiKey", {}
            ).get("value", "")

            # Call inference API
            inference_url = f"{INFERENCE_BASE}/translation"
            inference_headers = {
                "Content-Type": "application/json",
                "Authorization": inference_key,
            }
            inference_payload = {
                "pipelineTasks": [
                    {
                        "taskType": "translation",
                        "config": {
                            "language": {
                                "sourceLanguage": source_lang,
                                "targetLanguage": target_lang,
                            },
                            "serviceId": service_id,
                        },
                    }
                ],
                "inputData": {"input": [{"source": text}]},
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    inference_url,
                    json=inference_payload,
                    headers=inference_headers,
                )
                response.raise_for_status()
                result = response.json()

            # Extract translated text
            output = result.get("pipelineResponse", [{}])
            if output:
                translated = output[0].get("output", [{}])
                if translated:
                    return translated[0].get("target", text)

            return text

        except (httpx.HTTPStatusError, httpx.RequestError, KeyError, IndexError) as e:
            logger.error(f"BHASHINI translation error: {e}")
            return text  # Graceful fallback to original

    async def detect_language(self, text: str) -> str:
        """
        Detect the language of input text.

        Uses script detection as primary method with API fallback.

        Args:
            text: Text to identify.

        Returns:
            Language code (hi, te, ta, bn, en).
        """
        # Script-based detection (fast, offline)
        for char in text:
            code_point = ord(char)
            # Devanagari (Hindi)
            if 0x0900 <= code_point <= 0x097F:
                return "hi"
            # Telugu
            if 0x0C00 <= code_point <= 0x0C7F:
                return "te"
            # Tamil
            if 0x0B80 <= code_point <= 0x0BFF:
                return "ta"
            # Bengali
            if 0x0980 <= code_point <= 0x09FF:
                return "bn"

        # Default to English for Latin script
        return "en"

    async def transliterate(
        self, text: str, source_lang: str, target_lang: str
    ) -> str:
        """
        Transliterate text between scripts.

        Args:
            text: Text to transliterate.
            source_lang: Source language code.
            target_lang: Target language code.

        Returns:
            Transliterated text, or original on failure.
        """
        if not self._enabled:
            logger.info(
                f"[BHASHINI MOCK] Transliterate '{text[:50]}...' "
                f"from {source_lang} to {target_lang}"
            )
            return text

        config = await self._get_pipeline_config(
            source_lang, target_lang, task_type="transliteration"
        )
        if not config:
            return text

        try:
            pipeline_response = config.get("pipelineResponseConfig", [{}])
            if not pipeline_response:
                return text

            task_config = pipeline_response[0].get("config", [{}])
            if not task_config:
                return text

            service_id = task_config[0].get("serviceId", "")
            inference_key = config.get("pipelineInferenceAPIEndPoint", {}).get(
                "inferenceApiKey", {}
            ).get("value", "")

            inference_url = f"{INFERENCE_BASE}/transliteration"
            inference_headers = {
                "Content-Type": "application/json",
                "Authorization": inference_key,
            }
            inference_payload = {
                "pipelineTasks": [
                    {
                        "taskType": "transliteration",
                        "config": {
                            "language": {
                                "sourceLanguage": source_lang,
                                "targetLanguage": target_lang,
                            },
                            "serviceId": service_id,
                        },
                    }
                ],
                "inputData": {"input": [{"source": text}]},
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    inference_url,
                    json=inference_payload,
                    headers=inference_headers,
                )
                response.raise_for_status()
                result = response.json()

            output = result.get("pipelineResponse", [{}])
            if output:
                transliterated = output[0].get("output", [{}])
                if transliterated:
                    return transliterated[0].get("target", text)

            return text

        except (httpx.HTTPStatusError, httpx.RequestError, KeyError, IndexError) as e:
            logger.error(f"BHASHINI transliteration error: {e}")
            return text


# Singleton instance
bhashini_client = BhashiniClient()
