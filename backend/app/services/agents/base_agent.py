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
