"""
Provedor de embeddings: Google Gemini.

Usa a API de embeddings do Google AI (modelo text-embedding-004).
Requer a mesma GEMINI_API_KEY já configurada para o LLM.
"""

import logging

from google import genai

from app.services.embeddings.base import EmbeddingsProvider

logger = logging.getLogger(__name__)


class GeminiEmbeddingsProvider(EmbeddingsProvider):
    """Provedor de embeddings do Google Gemini."""

    def __init__(self, api_key: str, model: str):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    async def embed(self, text: str) -> list[float]:
        """Gera o vetor de embedding do texto via API do Gemini."""
        try:
            response = await self._client.aio.models.embed_content(
                model=self._model,
                contents=text,
            )
            if not response.embeddings:
                raise ValueError("Resposta de embeddings vazia do Gemini.")
            values = response.embeddings[0].values
            if not values:
                raise ValueError("Embedding vazio retornado pelo Gemini.")
            return list(values)
        except Exception as e:
            logger.exception("Erro ao gerar embedding no Gemini")
            raise RuntimeError(f"Erro ao gerar embedding no Gemini: {e}") from e

    async def health_check(self) -> bool:
        """Verifica conectividade com a API de embeddings."""
        try:
            vector = await self.embed("ping")
            return bool(vector)
        except Exception:
            logger.warning("Health check de embeddings Gemini falhou")
            return False
