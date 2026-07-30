"""
Provedor LLM: Groq.

Usa a API do Groq (compatível com formato OpenAI) para inferência ultrarrápida.
Free tier: ~30 req/min para modelos como Llama 3.3 70B.
"""

import logging

from groq import AsyncGroq

from app.services.llm.provider import LLMProvider


logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    """Provedor Groq para inferência rápida."""

    def __init__(self, api_key: str, model: str):
        self._client = AsyncGroq(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Envia prompt ao Groq e retorna resposta."""
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=4096,
                top_p=0.9,
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Resposta vazia do Groq.")

            return content.strip()

        except Exception as e:
            logger.exception("Erro na chamada ao Groq")
            raise RuntimeError(f"Erro ao comunicar com Groq: {e}") from e

    async def health_check(self) -> bool:
        """Verifica conectividade com Groq."""
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return bool(response.choices)
        except Exception:
            logger.warning("Health check Groq falhou")
            return False
