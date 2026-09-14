"""
Orquestrador de Múltiplos Agentes Inteligentes Especializados (MultiAgentOrchestrator).
"""

import asyncio
import logging
from typing import Any

from app.services.agents.agent_result import AgentOutcome, AgentResult
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
        Executa agentes em 2 fases. Early-exit da fase 2 SOMENTE se a fase 1
        concluiu com sucesso (ok_empty) em todos os agentes e zero achados.
        Falhas/parse_error NÃO disparam early-exit.
        """
        item_num = getattr(item, "item_number", "desconhecido")
        phase1 = self.agents[:2]
        phase2 = self.agents[2:]

        phase1_results = await self._run_phase(phase1, llm, item, legal_context)
        combined: list[dict[str, Any]] = []
        coverage_errors: list[str] = []

        phase1_all_ok_empty = True
        for res in phase1_results:
            if res.outcome == AgentOutcome.FINDINGS:
                phase1_all_ok_empty = False
                combined.extend(res.corrections)
            elif res.outcome == AgentOutcome.OK_EMPTY:
                continue
            else:
                phase1_all_ok_empty = False
                coverage_errors.append(f"{res.agent_id}:{res.outcome.value}")
                logger.error(
                    "Agente %s falhou no item %s (%s): %s",
                    res.agent_id,
                    item_num,
                    res.outcome.value,
                    res.error,
                )

        if phase1_all_ok_empty and not combined and not coverage_errors:
            logger.info(
                "Early-exit seguro no item %s: fase 1 ok_empty, pulando fase 2",
                item_num,
            )
            return []

        phase2_results = await self._run_phase(phase2, llm, item, legal_context)
        for res in phase2_results:
            if res.outcome == AgentOutcome.FINDINGS:
                combined.extend(res.corrections)
            elif res.outcome not in (AgentOutcome.OK_EMPTY, AgentOutcome.SKIPPED):
                coverage_errors.append(f"{res.agent_id}:{res.outcome.value}")
                logger.error(
                    "Agente %s falhou no item %s (%s): %s",
                    res.agent_id,
                    item_num,
                    res.outcome.value,
                    res.error,
                )

        deduplicated = self._deduplicate_corrections(combined)
        if coverage_errors:
            # Metadado consumido pelo engine para status completed_with_errors
            for corr in deduplicated:
                corr.setdefault("_coverage_errors", coverage_errors)
            if not deduplicated:
                deduplicated.append(
                    {
                        "category": "estrutural",
                        "severity": "alto",
                        "situation": "Cobertura incompleta de agentes",
                        "problem": (
                            "Um ou mais agentes falharam na análise deste item: "
                            + ", ".join(coverage_errors)
                        ),
                        "risk": "Análise incompleta — não tratar como item adequado.",
                        "original_text": getattr(item, "content", "")[:200] or "N/A",
                        "suggested_text": "Reexecutar a análise deste item.",
                        "justification": "Falha de cobertura multi-agente.",
                        "legal_basis": None,
                        "importance": "alta",
                        "agent_origin": "orchestrator",
                        "_coverage_errors": coverage_errors,
                    }
                )
        return deduplicated

    async def _run_phase(
        self,
        agents: list[BaseSpecializedAgent],
        llm: Any,
        item: Any,
        legal_context: str,
    ) -> list[AgentResult]:
        tasks = [
            agent.analyze_item(llm=llm, item=item, legal_context=legal_context)
            for agent in agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        typed: list[AgentResult] = []
        for agent, res in zip(agents, results, strict=False):
            if isinstance(res, AgentResult):
                typed.append(res)
            elif isinstance(res, Exception):
                typed.append(
                    AgentResult(
                        agent_id=agent.agent_id,
                        outcome=AgentOutcome.FAILED,
                        error=str(res),
                    )
                )
            else:
                typed.append(
                    AgentResult(
                        agent_id=agent.agent_id,
                        outcome=AgentOutcome.FAILED,
                        error="resultado inesperado",
                    )
                )
        return typed

    def _deduplicate_corrections(
        self, corrections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Remove duplicatas mantendo a correção de maior severidade.
        """
        severity_rank = {
            "info": 0,
            "baixo": 1,
            "medio": 2,
            "alto": 3,
            "critico": 4,
        }
        best_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        passthrough: list[dict[str, Any]] = []

        for corr in corrections:
            orig = (corr.get("original_text") or "").strip().lower()
            prob = (corr.get("problem") or "").strip().lower()
            if not orig or not prob:
                passthrough.append(corr)
                continue
            key = (orig, prob)
            existing = best_by_key.get(key)
            if existing is None:
                best_by_key[key] = corr
                continue
            new_rank = severity_rank.get(
                (corr.get("severity") or "").strip().lower(), -1
            )
            old_rank = severity_rank.get(
                (existing.get("severity") or "").strip().lower(), -1
            )
            if new_rank > old_rank:
                best_by_key[key] = corr

        return list(best_by_key.values()) + passthrough
