"""
Interface abstrata para provedores de embeddings (RAG Fase 4).

Factory pattern com failover automático entre provedores reais:
- Provider primário configurado via EMBEDDINGS_PROVIDER (gemini | ollama).
- Fallback automático para os demais provedores disponíveis.

A mesma filosofia do LLM vale aqui: nenhum mock em produção — apenas
provedores reais (API Gemini ou Ollama local).
"""

import asyncio
import logging
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingsProvider(ABC):
    """Interface base para provedores de embeddings."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Gera o vetor de embedding de um texto."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


class FailoverEmbeddingsProvider(EmbeddingsProvider):
    """Wrapper que tenta múltiplos provedores em ordem, com fallback."""

    def __init__(self, providers: list[EmbeddingsProvider]):
        if not providers:
            raise ValueError("Pelo menos um provider é obrigatório.")
        self._providers = providers
        self._last_successful: EmbeddingsProvider | None = None

    async def embed(self, text: str) -> list[float]:
        last_error: Exception | None = None
        for i, provider in enumerate(self._providers):
            try:
                vector = await asyncio.wait_for(
                    provider.embed(text),
                    timeout=settings.llm_timeout_seconds,
                )
                self._last_successful = provider
                if i > 0:
                    logger.info(
                        "Failover embeddings: %s/%s assumiu",
                        provider.provider_name, provider.model_name,
                    )
                return vector
            except Exception as e:
                last_error = e
                logger.warning(
                    "Provider de embeddings %s/%s falhou: %s. %s",
                    provider.provider_name, provider.model_name,
                    e,
                    "Tentando próximo..." if i < len(self._providers) - 1 else "Nenhum fallback restante.",
                )
        raise RuntimeError(
            f"Todos os provedores de embeddings falharam. Último erro: {last_error}"
        ) from last_error

    async def health_check(self) -> bool:
        for provider in self._providers:
            if await provider.health_check():
                self._last_successful = provider
                return True
        return False

    @property
    def provider_name(self) -> str:
        if self._last_successful:
            return self._last_successful.provider_name
        return self._providers[0].provider_name

    @property
    def model_name(self) -> str:
        if self._last_successful:
            return self._last_successful.model_name
        return self._providers[0].model_name


def _build_embeddings_providers() -> list[EmbeddingsProvider]:
    """Constrói lista de provedores reais disponíveis na ordem de prioridade."""
    providers: list[EmbeddingsProvider] = []
    primary = settings.embeddings_provider

    if primary == "gemini" and settings.gemini_api_key:
        from app.services.embeddings.gemini_provider import GeminiEmbeddingsProvider
        providers.append(GeminiEmbeddingsProvider(
            api_key=settings.gemini_api_key,
            model=settings.embeddings_model,
        ))

    if primary == "ollama":
        from app.services.embeddings.ollama_provider import OllamaEmbeddingsProvider
        providers.append(OllamaEmbeddingsProvider(
            base_url=settings.ollama_base_url,
            model=settings.embeddings_model,
        ))

    return providers


def get_embeddings_provider() -> EmbeddingsProvider:
    """
    Factory — retorna o provedor de embeddings configurado (com failover).

    Levanta RuntimeError se nenhum provedor real estiver disponível
    (chave de API ausente para o gemini e ollama indisponível).
    """
    providers = _build_embeddings_providers()

    if not providers:
        raise RuntimeError(
            "Nenhum provedor de embeddings configurado. Verifique "
            "EMBEDDINGS_PROVIDER e a chave GEMINI_API_KEY no .env."
        )

    if len(providers) == 1:
        return providers[0]

    logger.info(
        "Failover embeddings ativo: %s",
        " → ".join(p.provider_name for p in providers),
    )
    return FailoverEmbeddingsProvider(providers)
