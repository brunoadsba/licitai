"""Provedor LLM genérico via API compatível com OpenAI (/chat/completions).

Cobre Mistral La Plateforme, OpenRouter e HuggingFace Inference Providers
sem dependências novas (só httpx). Cada instância carrega um provider_name
distinto para o circuit breaker do failover tratar cotas separadamente.
"""

import logging
import time

import httpx

from app.services.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class OpenAICompatProvider(LLMProvider):
    """Chat completions estilo OpenAI contra qualquer base_url."""

    def __init__(
        self,
        provider_name: str,
        api_key: str,
        model: str,
        base_url: str,
        extra_headers: dict | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self._provider_name = provider_name
        self._model = model
        self._headers = {}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        if extra_headers:
            self._headers.update(extra_headers)
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers=self._headers,
        )

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model

    def _payload(self, system_prompt: str, user_prompt: str) -> dict:
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
            "top_p": 0.9,
        }

    @staticmethod
    def _extract_content(data: dict) -> str:
        try:
            return (data["choices"][0]["message"].get("content") or "").strip()
        except (KeyError, IndexError, TypeError, AttributeError):
            return ""

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Envia o prompt e retorna o texto da primeira escolha."""
        started = time.perf_counter()
        try:
            response = await self._client.post(
                "/chat/completions", json=self._payload(system_prompt, user_prompt)
            )
            if response.status_code == 429:
                raise RuntimeError(
                    f"Rate limit/quota no provedor {self._provider_name} "
                    f"(HTTP 429): {response.text[:300]}"
                )
            response.raise_for_status()
            content = self._extract_content(response.json())
            if not content:
                raise ValueError(f"Resposta vazia do {self._provider_name}.")
            usage = response.json().get("usage") or {}
            logger.info(
                "llm_usage provider=%s model=%s latency_ms=%d "
                "prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                self._provider_name,
                self._model,
                int((time.perf_counter() - started) * 1000),
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
            )
            return content
        except httpx.HTTPError as e:
            logger.exception("Erro HTTP na chamada ao %s", self._provider_name)
            raise RuntimeError(
                f"Erro ao comunicar com {self._provider_name}: {e}"
            ) from e
        except Exception as e:
            logger.exception("Erro na chamada ao %s", self._provider_name)
            raise RuntimeError(
                f"Erro ao comunicar com {self._provider_name}: {e}"
            ) from e

    async def health_check(self) -> bool:
        """Ping barato: uma geração mínima com 5 tokens."""
        try:
            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5,
                },
            )
            if response.status_code != 200:
                return False
            return bool(self._extract_content(response.json()))
        except Exception:
            logger.warning("Health check %s falhou", self._provider_name)
            return False
