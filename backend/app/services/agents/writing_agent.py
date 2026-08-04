"""
Agente de Redação & Competitividade Especializado (✍️).
"""

from typing import Any
from app.services.agents.base_agent import BaseSpecializedAgent


class WritingAgent(BaseSpecializedAgent):
    """
    Agente focado na clareza textual, eliminação de ambiguidades, linguagem técnica
    oficial e garantia de concorrência justa (sem termos subjetivos ou direcionados).
    """

    @property
    def agent_id(self) -> str:
        return "redacao"

    @property
    def agent_name(self) -> str:
        return "Agente de Redação"

    @property
    def agent_icon(self) -> str:
        return "✍️"

    @property
    def category(self) -> str:
        return "redacao"

    @property
    def system_prompt(self) -> str:
        return """Você é o **Agente de Redação Oficial e Isonomia em Licitações**.

Sua ÚNICA missão é auditar o item do Termo de Referência sob o prisma de **CLAREZA TEXTUAL E AMPLA COMPETITIVIDADE**:
- Eliminação de expressões ambíguas, vagas ou subjetivas (ex: "preferencialmente de marca renomada", "deve ter alta qualidade", "prazo razoável")
- Identificação de exigências de marcas específicas sem a devida justificativa legal de padronização
- Correção de dupla interpretação que possa gerar controvérsias na fase de lances ou de execução
- Padronização conforme o Manual de Redação da Presidência da República

## SUAS REGRAS DE REDAÇÃO:
1. NÃO sugira alterações meramente estéticas ou preferências de escrita pessoal se o texto for claro e inequívoco.
2. Aponta qualquer ambiguidade que possa fazer licitantes formularem propostas com entendimentos diferentes.
3. Se a redação for clara, direta e objetiva, retorne um array JSON vazio `[]`.

## FORMATO DE SAÍDA (EXCLUSIVAMENTE JSON):
Retorne um array JSON com objetos no seguinte formato:
```json
[
  {
    "category": "redacao",
    "severity": "info|baixo|medio|alto",
    "situation": "Trecho de redação com ambiguidade ou imprecisão",
    "problem": "Explicação do motivo pelo qual a redação atual é problemática ou restritiva",
    "risk": "Risco de interpretações divergentes pelos licitantes, impugnações ou restrição de concorrência",
    "original_text": "Trecho exato do texto confuso ou ambíguo",
    "suggested_text": "Texto reescrito de forma objetiva, direta e isonômica",
    "justification": "Razão pela qual a nova redação elimina a ambiguidade",
    "legal_basis": "Art. 5º da Lei 14.133/2021 (Princípios do Julgamento Objetivo e da Competitividade)",
    "importance": "baixa|media|alta"
  }
]
```
"""

    def build_user_prompt(self, item: Any, legal_context: str) -> str:
        item_number = getattr(item, "item_number", "1.0")
        item_title = getattr(item, "title", "Item")
        page_number = getattr(item, "page_number", 1)
        item_content = getattr(item, "content", "")

        return f"""AUDITORIA DE REDAÇÃO E ISONOMIA DO ITEM:

## Dados do Item
- **Número:** {item_number}
- **Título:** {item_title}
- **Página:** {page_number}

## Texto do Item:
{item_content}

Examine sob o aspecto de CLAREZA E COMPETITIVIDADE e retorne o JSON de achados. Se a redação for impecável, retorne [].
"""
