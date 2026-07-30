"""
Provedor LLM: Ollama (modelos locais).

Usa a API REST do Ollama para comunicação com modelos rodando localmente.
Suporta: Qwen3-32B, DeepSeek-R1, Llama 3.3, etc.
"""

import logging

import httpx

from app.services.llm.provider import LLMProvider


logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Provedor Ollama para modelos locais."""

    def __init__(self, base_url: str, model: str):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(300.0, connect=10.0),
        )

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Envia prompt ao Ollama e retorna resposta."""
        try:
            response = await self._client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 4096,
                    },
                },
            )
            response.raise_for_status()

            data = response.json()
            content = data.get("message", {}).get("content", "")

            if not content:
                raise ValueError("Resposta vazia do Ollama.")

            return content.strip()

        except httpx.HTTPError as e:
            logger.exception("Erro HTTP na chamada ao Ollama")
            raise RuntimeError(
                f"Erro ao comunicar com Ollama ({self._base_url}): {e}"
            ) from e
        except Exception as e:
            logger.exception("Erro na chamada ao Ollama")
            raise RuntimeError(f"Erro ao comunicar com Ollama: {e}") from e

    async def health_check(self) -> bool:
        """Verifica conectividade com Ollama."""
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            logger.warning("Health check Ollama falhou")
            return False
