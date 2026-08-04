"""
Testes do timeout configurável nas chamadas LLM (Fase 1 — Hardening).

Valida que o FailoverProvider aplica asyncio.wait_for com o timeout do
settings e que o failover tenta o próximo provedor após TimeoutError.
"""

import asyncio

import pytest

from app.services.llm.provider import FailoverProvider, LLMProvider


class ProviderLento(LLMProvider):
    """Provider que demora mais que o timeout configurado."""

    def __init__(self, atraso: float, nome: str = "lento"):
        self._atraso = atraso
        self._nome = nome

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        await asyncio.sleep(self._atraso)
        return f"resposta de {self._nome}"

    async def health_check(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return self._nome

    @property
    def model_name(self) -> str:
        return "modelo"


class ProviderRapido(LLMProvider):
    """Provider que responde imediatamente (fallback)."""

    def __init__(self, nome: str = "rapido"):
        self._nome = nome

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return f"resposta de {self._nome}"

    async def health_check(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return self._nome

    @property
    def model_name(self) -> str:
        return "modelo"


def test_timeout_ativo_propaga_e_nao_responde(monkeypatch):
    """Com timeout curto, um provider lento falha antes de responder."""
    from app.services.llm import provider as provider_module

    monkeypatch.setattr(provider_module.settings, "llm_timeout_seconds", 0.1)
    fp = FailoverProvider([ProviderLento(atraso=1.0)])

    with pytest.raises(RuntimeError):
        asyncio.run(fp.generate("sys", "user"))


def test_timeout_faz_failover_para_proximo_provider(monkeypatch):
    """Provider lento estoura o timeout e o próximo assume."""
    from app.services.llm import provider as provider_module

    monkeypatch.setattr(provider_module.settings, "llm_timeout_seconds", 0.1)
    fp = FailoverProvider([
        ProviderLento(atraso=1.0),
        ProviderRapido(nome="fallback"),
    ])

    resposta = asyncio.run(fp.generate("sys", "user"))
    assert resposta == "resposta de fallback"
    assert fp.provider_name == "fallback"


def test_sem_timeout_provider_normal_responde(monkeypatch):
    """Provider dentro do limite responde normalmente."""
    from app.services.llm import provider as provider_module

    monkeypatch.setattr(provider_module.settings, "llm_timeout_seconds", 5.0)
    fp = FailoverProvider([ProviderRapido(nome="primario")])

    resposta = asyncio.run(fp.generate("sys", "user"))
    assert resposta == "resposta de primario"
    assert fp.provider_name == "primario"
