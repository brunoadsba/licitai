"""
Interface abstrata para provedores de LLM.

Factory pattern com failover automático entre provedores reais:
- Provider primário configurado via LLM_PROVIDER
- Fallback automático para os demais provedores configurados
"""

import asyncio
import logging
from abc import ABC, abstractmethod

from app.config import settings


logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Interface base para todos os provedores de LLM."""

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
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


class FailoverProvider(LLMProvider):
    """
    Wrapper que tenta múltiplos provedores em ordem, com fallback automático.

    Se o primeiro falhar (timeout, erro de API, etc.), tenta o próximo,
    e assim por diante. Se todos falharem, levanta a exceção do último.
    """

    def __init__(self, providers: list[LLMProvider]):
        if not providers:
            raise ValueError("Pelo menos um provider é obrigatório.")
        self._providers = providers
        self._last_successful: LLMProvider | None = None

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        last_error: Exception | None = None
        for i, provider in enumerate(self._providers):
            try:
                response = await asyncio.wait_for(
                    provider.generate(system_prompt, user_prompt),
                    timeout=settings.llm_timeout_seconds,
                )
                self._last_successful = provider
                if i > 0:
                    logger.info(
                        "Failover: %s/%s assumiu após falha do primário",
                        provider.provider_name, provider.model_name,
                    )
                return response
            except Exception as e:
                last_error = e
                logger.warning(
                    "Provider %s/%s falhou: %s. %s",
                    provider.provider_name, provider.model_name,
                    e,
                    "Tentando próximo..." if i < len(self._providers) - 1 else "Nenhum fallback restante.",
                )
        raise RuntimeError(
            f"Todos os provedores LLM falharam. Último erro: {last_error}"
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


def _build_providers() -> list[LLMProvider]:
    """Constrói lista de provedores reais disponíveis na ordem de prioridade."""
    providers: list[LLMProvider] = []
    primary = settings.llm_provider

    def _add_gemini():
        if settings.gemini_api_key and not any(p.provider_name == "gemini" for p in providers):
            from app.services.llm.gemini_provider import GeminiProvider
            providers.append(GeminiProvider(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
            ))

    def _add_groq():
        if settings.groq_api_key and not any(p.provider_name == "groq" for p in providers):
            from app.services.llm.groq_provider import GroqProvider
            providers.append(GroqProvider(
                api_key=settings.groq_api_key,
                model=settings.groq_model,
            ))

    def _add_ollama():
        if not any(p.provider_name == "ollama" for p in providers):
            from app.services.llm.ollama_provider import OllamaProvider
            providers.append(OllamaProvider(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
            ))

    if primary == "gemini":
        _add_gemini()
        _add_groq()
    elif primary == "groq":
        _add_groq()
        _add_gemini()
    elif primary == "ollama":
        _add_ollama()
        _add_groq()
        _add_gemini()

    return providers


def get_llm_provider() -> LLMProvider:
    """
    Factory — retorna o melhor provedor LLM disponível com failover.

    A ordem de prioridade é definida pelo LLM_PROVIDER no .env:
    - gemini → Gemini → Groq
    - groq → Groq → Gemini (se chave presente)
    - ollama → Ollama

    Levanta RuntimeError se nenhum provedor real estiver configurado
    (chave de API ausente para o provedor primário e seus fallbacks).
    """
    providers = _build_providers()

    if not providers:
        raise RuntimeError(
            "Nenhum provedor LLM configurado. Verifique LLM_PROVIDER e "
            "as chaves de API (GEMINI_API_KEY/GROQ_API_KEY) no .env."
        )

    if len(providers) == 1:
        return providers[0]

    logger.info(
        "Failover ativo: %s → %s",
        providers[0].provider_name,
        " → ".join(p.provider_name for p in providers[1:]),
    )
    return FailoverProvider(providers)
