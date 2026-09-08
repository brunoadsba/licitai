"""
Testes de resiliência da camada LLM (auditoria):
- retry com backoff para erros transitórios
- timeout sem retry (failover direto)
- circuit breaker em 429/quota (cooldown pula o provedor esgotado)
- singleton de provedor preserva estado entre chamadas

E regressão do mapeamento de notas (_score_details): 0.0 legítimo ≠ ausente.
"""

import asyncio

import pytest

from app.services.llm import provider as provider_module
from app.services.llm.provider import (
    FailoverProvider,
    LLMProvider,
    _is_rate_limit_error,
    reset_llm_provider,
)


class ProviderControlado(LLMProvider):
    """Provider programável para simular falhas por chamada."""

    def __init__(self, nome: str, respostas: list[str | Exception]):
        self._nome = nome
        self._respostas = list(respostas)
        self.chamadas = 0

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.chamadas += 1
        resultado = self._respostas.pop(0) if self._respostas else "ok"
        if isinstance(resultado, Exception):
            raise resultado
        return f"{self._nome}:{resultado}"

    async def health_check(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return self._nome

    @property
    def model_name(self) -> str:
        return "modelo"


def _erro_429(nome: str = "groq") -> RuntimeError:
    return RuntimeError(f"Erro ao comunicar com {nome}: 429 rate limit exceeded")


def test_erro_transitorio_tem_retry_no_mesmo_provider():
    """Erro de rede genérico ganha 1 retry antes do failover."""
    primario = ProviderControlado("primario", [RuntimeError("connection reset"), "sucesso"])
    fp = FailoverProvider([primario])

    resposta = asyncio.run(fp.generate("sys", "user"))

    assert resposta == "primario:sucesso"
    assert primario.chamadas == 2


def test_timeout_nao_tem_retry_vai_direto_pro_fallback(monkeypatch):
    """Timeout já consumiu o orçamento de espera — failover imediato, sem retry."""
    monkeypatch.setattr(provider_module.settings, "llm_timeout_seconds", 0.05)

    class ProviderLento(LLMProvider):
        def __init__(self):
            self.chamadas = 0

        async def generate(self, system_prompt: str, user_prompt: str) -> str:
            self.chamadas += 1
            await asyncio.sleep(1.0)
            return "tarde demais"

        async def health_check(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "lento"

        @property
        def model_name(self) -> str:
            return "modelo"

    lento = ProviderLento()
    fallback = ProviderControlado("fallback", ["resposta"])
    fp = FailoverProvider([lento, fallback])

    resposta = asyncio.run(fp.generate("sys", "user"))

    assert resposta == "fallback:resposta"
    assert lento.chamadas == 1  # sem retry de timeout


def test_rate_limit_abre_circuit_e_proximas_chamadas_pulam_o_provider():
    """429 na 1ª chamada: fallback assume; 2ª chamada nem tenta o primário."""
    primario = ProviderControlado("primario", [_erro_429()])
    primario.respostas_infinitas = True
    # Depois da 1ª chamada, qualquer nova tentativa responderia bem —
    # mas o circuit breaker deve impedi-lo de ser acionado.
    fallback = ProviderControlado("fallback", ["r1", "r2"])
    fp = FailoverProvider([primario, fallback])

    primeira = asyncio.run(fp.generate("sys", "user"))
    segunda = asyncio.run(fp.generate("sys", "user"))

    assert primeira == "fallback:r1"
    assert segunda == "fallback:r2"
    assert primario.chamadas == 1  # pulado pelo circuit breaker


def test_todos_provedores_em_quota_levantam_runtime_error():
    a = ProviderControlado("a", [_erro_429("a")])
    b = ProviderControlado("b", [_erro_429("b")])
    fp = FailoverProvider([a, b])

    with pytest.raises(RuntimeError, match="Todos os provedores LLM falharam"):
        asyncio.run(fp.generate("sys", "user"))


def test_is_rate_limit_error_detecta_variacoes():
    assert _is_rate_limit_error(RuntimeError("429 RESOURCE_EXHAUSTED"))
    assert _is_rate_limit_error(RuntimeError("Rate limit reached for TPM"))
    assert _is_rate_limit_error(RuntimeError("quota exceeded"))
    assert not _is_rate_limit_error(RuntimeError("connection refused"))


def test_get_llm_provider_eh_singleton(monkeypatch):
    fake = ProviderControlado("fake", [])
    monkeypatch.setattr(provider_module, "_build_providers", lambda: [fake])
    reset_llm_provider()
    try:
        primeiro = provider_module.get_llm_provider()
        segundo = provider_module.get_llm_provider()
        assert primeiro is segundo
    finally:
        reset_llm_provider()


def test_reset_llm_provider_permite_reconstruir(monkeypatch):
    from app.services.llm.limiter import LimitedLLMProvider

    fake1 = ProviderControlado("fake1", [])
    fake2 = ProviderControlado("fake2", [])
    monkeypatch.setattr(provider_module, "_build_providers", lambda: [fake1])
    reset_llm_provider()
    try:
        primeiro = provider_module.get_llm_provider()
        monkeypatch.setattr(provider_module, "_build_providers", lambda: [fake2])
        reset_llm_provider()
        segundo = provider_module.get_llm_provider()
        assert primeiro is not segundo
        inner = (
            segundo._inner
            if isinstance(segundo, LimitedLLMProvider)
            else segundo
        )
        assert inner is fake2
    finally:
        reset_llm_provider()


def test_score_details_preserva_zero_legitimo():
    """Regressão M1: nota 0.0 é válida e não pode virar null."""
    from types import SimpleNamespace

    from app.api.analysis import _score_details

    analysis = SimpleNamespace(
        score_overall=0.0,
        score_juridical=None,
        score_technical=7.5,
        score_writing=None,
        score_structural=10.0,
    )
    detalhes = _score_details(analysis)

    assert [d.score for d in detalhes] == [0.0, None, 7.5, None, 10.0]
