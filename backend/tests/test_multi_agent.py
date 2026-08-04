"""
Testes Unitários da Arquitetura de Múltiplos Agentes Inteligentes Especializados.
"""

import asyncio
import pytest
from app.services.agents.base_agent import BaseSpecializedAgent
from app.services.agents.legal_agent import LegalAgent
from app.services.agents.technical_agent import TechnicalAgent
from app.services.agents.writing_agent import WritingAgent
from app.services.agents.structural_agent import StructuralAgent
from app.services.agents.orchestrator import MultiAgentOrchestrator
from app.services.llm.provider import LLMProvider


class FakeAgentProvider(LLMProvider):
    """Provider Fake para testes de agentes sem chamada real de API."""

    def __init__(self, response_text: str):
        self.response_text = response_text

    @property
    def provider_name(self) -> str:
        return "fake_agent"

    @property
    def model_name(self) -> str:
        return "fake-model"

    async def health_check(self) -> bool:
        return True

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return self.response_text

    async def _generate_implementation(self, prompt: str, system_prompt: str | None = None) -> str:
        return self.response_text


class DummyItem:
    def __init__(self, item_number="1.1", title="Objeto", page_number=1, content="Texto do item"):
        self.item_number = item_number
        self.title = title
        self.page_number = page_number
        self.content = content


def test_agent_properties():
    """Valida identificadores, nomes e emojis dos 4 agentes especializados."""
    legal = LegalAgent()
    tech = TechnicalAgent()
    writing = WritingAgent()
    struct = StructuralAgent()

    assert legal.agent_id == "juridico"
    assert legal.agent_icon == "⚖️"
    assert legal.category == "juridica"

    assert tech.agent_id == "tecnico"
    assert tech.agent_icon == "🛠️"
    assert tech.category == "tecnica"

    assert writing.agent_id == "redacao"
    assert writing.agent_icon == "✍️"
    assert writing.category == "redacao"

    assert struct.agent_id == "estrutural"
    assert struct.agent_icon == "📐"
    assert struct.category == "estrutural"


def test_legal_agent_analysis():
    """O Agente Jurídico analisa um item e insere a tag agent_origin='juridico'."""
    async def _run():
        fake_json = """[
          {
            "category": "juridica",
            "severity": "alto",
            "situation": "Exigência de atestado sem limitação",
            "problem": "Restrição ilegal",
            "risk": "Impugnação",
            "original_text": "Atestado exclusivo",
            "suggested_text": "Atestado pertinente",
            "justification": "Art. 67 da Lei 14.133/21",
            "legal_basis": "Art. 67 da Lei 14.133/21",
            "importance": "alta"
          }
        ]"""
        provider = FakeAgentProvider(fake_json)
        agent = LegalAgent()
        item = DummyItem()

        corrections = await agent.analyze_item(provider, item, "Contexto legal")

        assert len(corrections) == 1
        assert corrections[0]["agent_origin"] == "juridico"
        assert corrections[0]["category"] == "juridica"
        assert corrections[0]["legal_basis"] == "Art. 67 da Lei 14.133/21"

    asyncio.run(_run())


def test_orchestrator_runs_all_agents():
    """O Orquestrador executa todos os 4 agentes em paralelo e agrega os resultados."""
    async def _run():
        fake_json = """[
          {
            "category": "tecnica",
            "severity": "medio",
            "situation": "Especificação vaga",
            "problem": "Falta SLA",
            "risk": "Má qualidade",
            "original_text": "Alta qualidade",
            "suggested_text": "SLA 99.9%",
            "justification": "Garantir desempenho",
            "legal_basis": "Art. 6º, XXIII da Lei 14.133/21",
            "importance": "media"
          }
        ]"""
        provider = FakeAgentProvider(fake_json)
        orchestrator = MultiAgentOrchestrator()
        item = DummyItem()

        corrections = await orchestrator.analyze_item_multi(provider, item, "Contexto")

        assert len(corrections) >= 1
        assert "agent_origin" in corrections[0]

    asyncio.run(_run())


def test_orchestrator_deduplication():
    """O Orquestrador remove duplicatas idênticas."""
    orchestrator = MultiAgentOrchestrator()
    raw = [
        {"original_text": "abc", "problem": "prob1", "agent_origin": "juridico"},
        {"original_text": "abc", "problem": "prob1", "agent_origin": "tecnico"},
        {"original_text": "xyz", "problem": "prob2", "agent_origin": "redacao"},
    ]

    dedup = orchestrator._deduplicate_corrections(raw)

    assert len(dedup) == 2
    assert dedup[0]["agent_origin"] == "juridico"
    assert dedup[1]["agent_origin"] == "redacao"
