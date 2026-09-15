"""Regressão auditoria 15/09: is_last_provider deve usar lista filtrada por cooldown."""

import asyncio
import time

from app.services.llm.provider import FailoverProvider, LLMProvider


class ProviderControlado(LLMProvider):
    def __init__(self, nome: str, respostas: list):
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


def test_is_last_usa_lista_filtrada_com_cooldown():
    """Com 1 provider em cooldown, o único disponível é last (sem 'Tentando próximo')."""
    ruim = ProviderControlado("ruim", [RuntimeError("429 rate limit exceeded")])
    bom = ProviderControlado("bom", ["sucesso"])
    fp = FailoverProvider([ruim, bom])
    # Força cooldown no primeiro
    fp._cooldown_until[0] = time.monotonic() + 30.0

    ordered = fp._ordered_providers()
    assert len(ordered) == 1
    assert ordered[0][1].provider_name == "bom"

    resposta = asyncio.run(fp.generate("sys", "user"))
    assert resposta == "bom:sucesso"
    assert bom.chamadas == 1
    assert ruim.chamadas == 0
