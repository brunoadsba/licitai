"""
Provedor de embeddings: Ollama (local).

Usa o endpoint /api/embeddings do servidor Ollama com modelos de embeddings
(ex.: bge-m3, nomic-embed-text). Sem necessidade de chave de API.
"""

import logging

import httpx

from app.services.embeddings.base import EmbeddingsProvider

logger = logging.getLogger(__name__)


class OllamaEmbeddingsProvider(EmbeddingsProvider):
    """Provedor de embeddings via Ollama local."""

    def __init__(self, base_url: str, model: str):
        self._base_url = base_url.rstrip("/")
        self._model = model

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def embed(self, text: str) -> list[float]:
        """Gera o vetor de embedding via API local do Ollama."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text},
                )
                response.raise_for_status()
                vector = response.json().get("embedding")
            if not vector:
                raise ValueError("Embedding vazio retornado pelo Ollama.")
            return list(vector)
        except Exception as e:
            logger.exception("Erro ao gerar embedding no Ollama")
            raise RuntimeError(f"Erro ao gerar embedding no Ollama: {e}") from e

    async def health_check(self) -> bool:
        """Verifica se o modelo de embeddings está disponível no Ollama."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": "ping"},
                )
                return response.status_code == 200
        except Exception:
            logger.warning("Health check de embeddings Ollama falhou")
            return False
