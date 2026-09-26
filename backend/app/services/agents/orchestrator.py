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
        combined, phase1_all_ok_empty, coverage_errors = self._fold_phase_results(
            item_num, phase1_results, track_ok_empty=True
        )

        if phase1_all_ok_empty and not combined and not coverage_errors:
            logger.info(
                "Early-exit seguro no item %s: fase 1 ok_empty, pulando fase 2",
                item_num,
            )
            return []

        phase2_results = await self._run_phase(phase2, llm, item, legal_context)
        phase2_combined, _, phase2_errors = self._fold_phase_results(
            item_num, phase2_results, track_ok_empty=False
        )
        combined.extend(phase2_combined)
        coverage_errors.extend(phase2_errors)

        return self._apply_coverage_errors(item, combined, coverage_errors)

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

    def _fold_phase_results(
        self,
        item_num: str,
        phase_results: list[AgentResult],
        *,
        track_ok_empty: bool,
    ) -> tuple[list[dict[str, Any]], bool, list[str]]:
        """Dobra resultados de uma fase no mesmo padrão do fluxo unitário."""
        combined: list[dict[str, Any]] = []
        coverage_errors: list[str] = []
        all_ok_empty = True
        for res in phase_results:
            if res.outcome == AgentOutcome.FINDINGS:
                if track_ok_empty:
                    all_ok_empty = False
                combined.extend(res.corrections)
            elif res.outcome in (AgentOutcome.OK_EMPTY, AgentOutcome.SKIPPED):
                continue
            else:
                if track_ok_empty:
                    all_ok_empty = False
                coverage_errors.append(f"{res.agent_id}:{res.outcome.value}")
                logger.error(
                    "Agente %s falhou no item %s (%s): %s",
                    res.agent_id,
                    item_num,
                    res.outcome.value,
                    res.error,
                )
        return combined, all_ok_empty, coverage_errors

    def _apply_coverage_errors(
        self, item: Any, corrections: list[dict[str, Any]], coverage_errors: list[str]
    ) -> list[dict[str, Any]]:
        """Anexa metadados de cobertura e o pseudo-achado operacional padrão."""
        deduplicated = self._deduplicate_corrections(corrections)
        if coverage_errors:
            for corr in deduplicated:
                corr.setdefault("_coverage_errors", coverage_errors)
            if not deduplicated:
                deduplicated.append(
                    {
                        "category": "estructural",
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

    async def analyze_batch_multi(
        self, llm: Any, batch: list[tuple[Any, str]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Analisa um lote de (item, contexto) com UMA chamada por agente/fase.

        Preserva a semântica do fluxo unitário por item: fases, early-exit
        individual (fase 2 só roda para itens sem ok_empty total) e
        pseudo-achado de cobertura por item em caso de falha.
        """
        phase1 = self.agents[:2]
        phase2 = self.agents[2:]

        phase1_out = await self._run_batch_phase(phase1, llm, batch)

        combined: dict[str, list[dict[str, Any]]] = {}
        errors: dict[str, list[str]] = {}
        need_phase2: list[tuple[Any, str]] = []
        for item, _ctx in batch:
            item_id = str(item.id)
            item_num = getattr(item, "item_number", "desconhecido")
            results = [phase1_out[agent.agent_id].get(item_id) for agent in phase1]
            results = [r for r in results if r is not None]
            corr, all_ok, errs = self._fold_phase_results(
                item_num, results, track_ok_empty=True
            )
            combined[item_id] = corr
            errors[item_id] = errs
            if all_ok and not corr and not errs:
                logger.info(
                    "Early-exit seguro no item %s: fase 1 ok_empty, pulando fase 2",
                    item_num,
                )
            else:
                need_phase2.append((item, _ctx))

        if need_phase2 and phase2:
            phase2_out = await self._run_batch_phase(phase2, llm, need_phase2)
            for item, _ctx in need_phase2:
                item_id = str(item.id)
                item_num = getattr(item, "item_number", "desconhecido")
                results = [
                    phase2_out[agent.agent_id].get(item_id) for agent in phase2
                ]
                results = [r for r in results if r is not None]
                corr, _, errs = self._fold_phase_results(
                    item_num, results, track_ok_empty=False
                )
                combined[item_id].extend(corr)
                errors[item_id].extend(errs)

        return {
            str(item.id): self._apply_coverage_errors(
                item, combined[str(item.id)], errors[str(item.id)]
            )
            for item, _ in batch
        }

    async def _run_batch_phase(
        self,
        agents: list[BaseSpecializedAgent],
        llm: Any,
        batch: list[tuple[Any, str]],
    ) -> dict[str, dict[str, AgentResult]]:
        """Roda uma fase em lote: {agent_id: {item_id: AgentResult}}."""
        tasks = [agent.analyze_batch(llm=llm, batch=batch) for agent in agents]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        mapped: dict[str, dict[str, AgentResult]] = {}
        for agent, res in zip(agents, outcomes, strict=False):
            if isinstance(res, dict):
                mapped[agent.agent_id] = res
            else:
                err = res if isinstance(res, Exception) else Exception("resultado inesperado")
                mapped[agent.agent_id] = {
                    str(item.id): AgentResult(
                        agent_id=agent.agent_id,
                        outcome=AgentOutcome.FAILED,
                        error=str(err),
                    )
                    for item, _ in batch
                }
        return mapped

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
