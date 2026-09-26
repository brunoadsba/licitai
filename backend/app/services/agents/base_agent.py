"""
Classe abstrata base para Agentes Especializados em Análise de TR.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.services.agents.agent_result import AgentOutcome, AgentResult
from app.services.analyzer.json_utils import (
    parse_json_response,
    sanitize_correction,
    validate_correction,
)

logger = logging.getLogger(__name__)


class BaseSpecializedAgent(ABC):
    """
    Classe base para agentes especializados de análise.
    Cada agente possui foco, persona e escopo de verificação específicos.
    """

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Identificador único do agente (ex: 'juridico', 'tecnico', 'redacao', 'estrutural')."""
        pass

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Nome amigável em PT-BR (ex: 'Agente Jurídico')."""
        pass

    @property
    @abstractmethod
    def agent_icon(self) -> str:
        """Emoji/ícone representativo (ex: '⚖️')."""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Categoria primária de correções associadas (ex: 'juridica', 'tecnica', 'redacao', 'estrutural')."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt especializado com persona e regras do agente."""
        pass

    @abstractmethod
    def build_user_prompt(self, item: Any, legal_context: str) -> str:
        """Monta o user prompt direcionado ao escopo do agente."""
        pass

    async def analyze_item(self, llm: Any, item: Any, legal_context: str) -> AgentResult:
        """
        Executa a análise do item pelo agente especializado.
        Retorna AgentResult tipado (nunca mascara falha como lista vazia).
        """
        user_prompt = self.build_user_prompt(item, legal_context)
        item_num = getattr(item, "item_number", "desconhecido")

        try:
            raw_response = await llm.generate(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
            )
        except Exception as e:
            logger.warning(
                "Falha na análise do agente %s para o item %s: %s",
                self.agent_id,
                item_num,
                str(e),
            )
            return AgentResult(
                agent_id=self.agent_id,
                outcome=AgentOutcome.FAILED,
                error=str(e),
            )

        try:
            corrections = parse_json_response(raw_response)
        except Exception as e:
            logger.warning(
                "Parse error no agente %s item %s: %s",
                self.agent_id,
                item_num,
                str(e),
            )
            return AgentResult(
                agent_id=self.agent_id,
                outcome=AgentOutcome.PARSE_ERROR,
                error=str(e),
            )

        valid_corrections = []
        for corr in corrections:
            if validate_correction(corr):
                sanitized = sanitize_correction(corr)
                sanitized["category"] = self.category
                sanitized["agent_origin"] = self.agent_id
                valid_corrections.append(sanitized)

        if valid_corrections:
            return AgentResult(
                agent_id=self.agent_id,
                outcome=AgentOutcome.FINDINGS,
                corrections=valid_corrections,
            )
        return AgentResult(
            agent_id=self.agent_id,
            outcome=AgentOutcome.OK_EMPTY,
            corrections=[],
        )

    async def analyze_batch(
        self, llm: Any, batch: list[tuple[Any, str]]
    ) -> dict[str, AgentResult]:
        """Analisa um lote de (item, contexto) em UMA chamada LLM.

        Cada correção da resposta precisa carregar `item_number` válido do
        lote; o roteamento usa `split_corrections_by_item` (atribuição
        desconhecida é descartada, nunca remapeada). Falha de chamada ou de
        parse vira FAILED/PARSE_ERROR para todos os itens do lote, preservando
        a semântica de cobertura do fluxo unitário.
        """
        from app.services.analyzer.batching import (
            BATCH_ATTRIBUTION_INSTRUCTION,
            batch_numbers_label,
            split_corrections_by_item,
        )

        numbers = batch_numbers_label(batch)
        sections = []
        for item, legal_context in batch:
            sections.append(
                f"=== ITEM {getattr(item, 'item_number', '?')} ===\n"
                + self.build_user_prompt(item, legal_context)
            )
        user_prompt = (
            f"AUDITORIA MULTIAGENTE EM LOTE — {self.agent_name} "
            f"({self.agent_id})\n"
            + BATCH_ATTRIBUTION_INSTRUCTION.format(n=len(batch), numbers=numbers)
            + "\n\n"
            + "\n\n".join(sections)
        )

        try:
            raw_response = await llm.generate(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
            )
        except Exception as e:
            logger.warning(
                "Falha na análise em lote do agente %s (%d itens): %s",
                self.agent_id,
                len(batch),
                str(e),
            )
            return {
                str(item.id): AgentResult(
                    agent_id=self.agent_id,
                    outcome=AgentOutcome.FAILED,
                    error=str(e),
                )
                for item, _ in batch
            }

        try:
            corrections = parse_json_response(raw_response)
        except Exception as e:
            logger.warning(
                "Parse error em lote no agente %s: %s", self.agent_id, str(e)
            )
            return {
                str(item.id): AgentResult(
                    agent_id=self.agent_id,
                    outcome=AgentOutcome.PARSE_ERROR,
                    error=str(e),
                )
                for item, _ in batch
            }

        if isinstance(corrections, dict):
            corrections = [corrections]
        if not isinstance(corrections, list):
            corrections = []

        valid = [
            c
            for c in corrections
            if isinstance(c, dict) and validate_correction(c)
        ]
        routed = split_corrections_by_item(batch, valid)

        results: dict[str, AgentResult] = {}
        for item, _ in batch:
            item_id = str(item.id)
            sanitized = []
            for corr in routed[item_id]:
                clean = sanitize_correction(corr)
                clean["category"] = self.category
                clean["agent_origin"] = self.agent_id
                sanitized.append(clean)
            if sanitized:
                results[item_id] = AgentResult(
                    agent_id=self.agent_id,
                    outcome=AgentOutcome.FINDINGS,
                    corrections=sanitized,
                )
            else:
                results[item_id] = AgentResult(
                    agent_id=self.agent_id,
                    outcome=AgentOutcome.OK_EMPTY,
                    corrections=[],
                )
        return results
