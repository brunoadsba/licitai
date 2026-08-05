"""
Adaptador de provedor LLM para o Copiloto.

Define um protocolo mínimo para o chat e duas implementações:

- `ExistingChatLLM`: usa o `get_llm_provider()` já existente (com failover),
  chamando `.generate(system_prompt, user_prompt)`.
- `FakeChatLLM`: determinístico, usado em testes e quando
  `chat_force_fake_provider=True` (demo/CI sem chaves de API).

O retorno esperado do LLM é um JSON com a forma:

    {
      "answer": "texto da resposta",
      "grounded": true,
      "confidence": 0.9,
      "citations": [{"type": "legal", "reference": "...", "title": "...", "snippet": "..."}],
      "suggested_actions": [{"action": "...", "description": "..."}]
    }
"""

import json
import logging

from app.config import settings
from app.services.llm.provider import get_llm_provider


logger = logging.getLogger(__name__)


class ChatLLMProvider:
    """Protocolo mínimo de provedor LLM para o chat."""

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    @property
    def provider_name(self) -> str:
        raise NotImplementedError

    @property
    def model_name(self) -> str:
        raise NotImplementedError


class ExistingChatLLM(ChatLLMProvider):
    """Usa o provider LLM existente (com failover)."""

    def __init__(self) -> None:
        self._inner = get_llm_provider()

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return await self._inner.generate(system_prompt, user_prompt)

    @property
    def provider_name(self) -> str:
        return self._inner.provider_name

    @property
    def model_name(self) -> str:
        return self._inner.model_name


class FakeChatLLM(ChatLLMProvider):
    """
    Resposta fake determinística, no formato JSON esperado pelo validator.

    Nunca é usada em produção com chaves reais: serve para testes e para o
    modo `chat_force_fake_provider=True`.
    """

    def __init__(self, answer: str = "Resposta de demonstração.") -> None:
        self._answer = answer

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return json.dumps(
            {
                "answer": self._answer,
                "grounded": True,
                "confidence": 0.9,
                "citations": [
                    {
                        "type": "legal",
                        "reference": "Lei 14.133/2021, art. 5º",
                        "title": "Lei 14.133/2021",
                        "snippet": "A contratação de obras, serviços e compras...",
                    }
                ],
                "suggested_actions": [],
            },
            ensure_ascii=False,
        )

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-chat"


def get_chat_llm() -> ChatLLMProvider:
    """Factory do provedor de chat, respeitando `chat_force_fake_provider`."""
    if settings.chat_force_fake_provider:
        logger.warning(
            "Usando FakeChatLLM (chat_force_fake_provider=True). "
            "Nenhuma resposta será gerada por IA real."
        )
        return FakeChatLLM()
    return ExistingChatLLM()
