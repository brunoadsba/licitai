"""
Orquestrador de Múltiplos Agentes Inteligentes Especializados (MultiAgentOrchestrator).
"""

import asyncio
import logging
from typing import Any

from app.services.agents.base_agent import BaseSpecializedAgent
from app.services.agents.legal_agent import LegalAgent
from app.services.agents.structural_agent import StructuralAgent
from app.services.agents.technical_agent import TechnicalAgent
from app.services.agents.writing_agent import WritingAgent

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
        Executa os agentes em 2 fases para economia: se Jurídico+Técnico
        retornarem vazio com confiança, pula Redação+Estrutural. Provedor
        por etapa: Groq para extração rápida, Gemini para fundamentação (quando
        llm suporta failover, a escolha é transparente).
        """
        item_num = getattr(item, "item_number", "desconhecido")
        phase1 = self.agents[:2]
        phase2 = self.agents[2:]

        phase1_tasks = [
            agent.analyze_item(llm=llm, item=item, legal_context=legal_context)
            for agent in phase1
        ]
        phase1_results = await asyncio.gather(*phase1_tasks, return_exceptions=True)

        combined_corrections: list[dict[str, Any]] = []
        empty_phase1 = 0
        for agent, res in zip(phase1, phase1_results, strict=False):
            if isinstance(res, Exception):
                logger.error(
                    "Exceção no agente %s no item %s: %s",
                    agent.agent_id,
                    item_num,
                    str(res),
                )
                empty_phase1 += 1
                continue
            if isinstance(res, list):
                if not res:
                    empty_phase1 += 1
                combined_corrections.extend(res)

        if empty_phase1 == len(phase1) and not combined_corrections:
            logger.info("Early-exit no item %s: fase 1 vazia, pulando fase 2", item_num)
            return []

        phase2_tasks = [
            agent.analyze_item(llm=llm, item=item, legal_context=legal_context)
            for agent in phase2
        ]
        phase2_results = await asyncio.gather(*phase2_tasks, return_exceptions=True)
        for agent, res in zip(phase2, phase2_results, strict=False):
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
