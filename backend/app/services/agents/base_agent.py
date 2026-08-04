"""
Classe abstrata base para Agentes Especializados em Análise de TR.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any

from app.services.analyzer.json_utils import parse_json_response, validate_correction, sanitize_correction

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

    async def analyze_item(self, llm: Any, item: Any, legal_context: str) -> list[dict[str, Any]]:
        """
        Executa a análise do item pelo agente especializado.
        Retorna a lista de correções encontradas com a tag `agent_origin`.
        """
        user_prompt = self.build_user_prompt(item, legal_context)

        try:
            raw_response = await llm.generate(
                prompt=user_prompt,
                system_prompt=self.system_prompt,
            )
            corrections = parse_json_response(raw_response)

            valid_corrections = []
            for corr in corrections:
                if validate_correction(corr):
                    sanitized = sanitize_correction(corr)
                    # Forçar categoria primária do agente se ausente/divergente
                    sanitized["category"] = self.category
                    sanitized["agent_origin"] = self.agent_id
                    valid_corrections.append(sanitized)

            return valid_corrections

        except Exception as e:
            logger.warning(
                "Falha na análise do agente %s para o item %s: %s",
                self.agent_id,
                getattr(item, "item_number", "desconhecido"),
                str(e),
            )
            return []
