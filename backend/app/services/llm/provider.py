"""
Interface abstrata para provedores de LLM.

Factory pattern que instancia o provider correto baseado na configuração.
"""

import logging
from abc import ABC, abstractmethod

from app.config import settings


logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Interface base para todos os provedores de LLM."""

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Envia prompt ao LLM e retorna a resposta.

        Args:
            system_prompt: Instruções do sistema (persona do especialista).
            user_prompt: Prompt do usuário com o item a analisar.

        Returns:
            Resposta do LLM como string.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica se o provedor está acessível."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nome do provedor para logging."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Nome do modelo em uso."""
        ...


def get_llm_provider() -> LLMProvider:
    """
    Factory — retorna o provedor LLM configurado.

    Raises:
        ValueError: Se o provedor configurado não é válido ou
                    as credenciais necessárias não estão disponíveis.
    """
    provider = settings.llm_provider

    if provider == "groq":
        if not settings.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY não configurada. "
                "Defina no arquivo .env para usar o Groq."
            )
        from app.services.llm.groq_provider import GroqProvider
        return GroqProvider(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
        )

    elif provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY não configurada. "
                "Defina no arquivo .env para usar o Google Gemini."
            )
        from app.services.llm.gemini_provider import GeminiProvider
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )

    elif provider == "ollama":
        from app.services.llm.ollama_provider import OllamaProvider
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

    else:
        raise ValueError(
            f"Provedor LLM não suportado: '{provider}'. "
            f"Use: groq, gemini ou ollama."
        )
