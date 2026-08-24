"""
Provedor LLM: Google Gemini.

Usa a API do Google AI (Generative AI) para inferência.
Free tier: 1500 req/dia para Gemini 2.0 Flash.
"""

import logging
import time

from google import genai
from google.genai import types

from app.services.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Provedor Google Gemini."""

    def __init__(self, api_key: str, model: str):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Envia prompt ao Gemini e retorna resposta."""
        started = time.perf_counter()
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                    top_p=0.9,
                    max_output_tokens=4096,
                ),
            )

            if not response.text:
                raise ValueError("Resposta vazia do Gemini.")

            usage = getattr(response, "usage_metadata", None)
            logger.info(
                "llm_usage provider=gemini model=%s latency_ms=%d "
                "prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                self._model,
                int((time.perf_counter() - started) * 1000),
                getattr(usage, "prompt_token_count", None),
                getattr(usage, "candidates_token_count", None),
                getattr(usage, "total_token_count", None),
            )
            return response.text.strip()

        except Exception as e:
            logger.exception("Erro na chamada ao Gemini")
            raise RuntimeError(f"Erro ao comunicar com Gemini: {e}") from e

    async def health_check(self) -> bool:
        """Verifica conectividade com Gemini."""
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents="ping",
                config=types.GenerateContentConfig(max_output_tokens=5),
            )
            return bool(response.text)
        except Exception:
            logger.warning("Health check Gemini falhou")
            return False
