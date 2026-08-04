"""
Orquestrador de Múltiplos Agentes Inteligentes Especializados (MultiAgentOrchestrator).
"""

import asyncio
import logging
from typing import Any

from app.services.agents.base_agent import BaseSpecializedAgent
from app.services.agents.legal_agent import LegalAgent
from app.services.agents.technical_agent import TechnicalAgent
from app.services.agents.writing_agent import WritingAgent
from app.services.agents.structural_agent import StructuralAgent

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    Orquestra a execução simultânea dos 4 agentes especializados (Jurídico, Técnico,
    Redação, Estrutural) para a análise detalhada de cada item do Termo de Referência.
    """

    def __init__(self, agents: list[BaseSpecializedAgent] | None = None):
        if agents is None:
            self.agents: list[BaseSpecializedAgent] = [
                LegalAgent(),
                TechnicalAgent(),
                WritingAgent(),
                StructuralAgent(),
            ]
        else:
            self.agents = agents

    async def analyze_item_multi(
        self, llm: Any, item: Any, legal_context: str
    ) -> list[dict[str, Any]]:
        """
        Executa os agentes especializados em paralelo via asyncio.gather,
        combina e deduplica os achados do item.
        """
        item_num = getattr(item, "item_number", "desconhecido")
        tasks = [
            agent.analyze_item(llm=llm, item=item, legal_context=legal_context)
            for agent in self.agents
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        combined_corrections: list[dict[str, Any]] = []

        for agent, res in zip(self.agents, results):
            if isinstance(res, Exception):
                logger.error(
                    "Exceção no agente %s no item %s: %s",
                    agent.agent_id,
                    item_num,
                    str(res),
                )
                continue
            if isinstance(res, list):
                combined_corrections.extend(res)

        # Deduplicação baseada em texto original + problema idêntico
        deduplicated = self._deduplicate_corrections(combined_corrections)
        return deduplicated

    def _deduplicate_corrections(
        self, corrections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Remove duplicatas mantendo a correção de maior severidade/especificidade.
        """
        seen: set[tuple[str, str]] = set()
        unique_list: list[dict[str, Any]] = []

        for corr in corrections:
            orig = (corr.get("original_text") or "").strip().lower()
            prob = (corr.get("problem") or "").strip().lower()
            key = (orig, prob)

            if key in seen and orig and prob:
                continue

            if orig and prob:
                seen.add(key)
            unique_list.append(corr)

        return unique_list
