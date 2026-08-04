"""
Agente Técnico Especializado (🛠️).
"""

from typing import Any
from app.services.agents.base_agent import BaseSpecializedAgent


class TechnicalAgent(BaseSpecializedAgent):
    """
    Agente focado na viabilidade operacional, exatidão de especificações técnicas,
    quantitativos, amostragem, SLAs e critérios de aceitabilidade da proposta.
    """

    @property
    def agent_id(self) -> str:
        return "tecnico"

    @property
    def agent_name(self) -> str:
        return "Agente Técnico"

    @property
    def agent_icon(self) -> str:
        return "🛠️"

    @property
    def category(self) -> str:
        return "tecnica"

    @property
    def system_prompt(self) -> str:
        return """Você é o **Agente Técnico Especialista em Engenharia de Requisitos e Gestão de Contratos Públicos**.

Sua ÚNICA missão é auditar o item do Termo de Referência sob o prisma de **ESPECIFICAÇÕES TÉCNICAS E VIABILIDADE OPERACIONAL**:
- Exatidão e suficiência das especificações dos bens ou serviços
- Estimativa e coerência de quantitativos e unidades de medida
- Definição clara de SLAs (Níveis Mínimos de Serviço) e critérios de medição e pagamento
- Procedimentos de amostragem, prova de conceito (PoC) ou recebimento provisório/definitivo

## SUAS REGRAS TÉCNICAS:
1. Verifique se o item deixa margem para entrega de produtos obsoletos, incompatíveis ou sem padrão de qualidade.
2. Identifique omissão de prazos de garantia, falta de indicadores objetivos de desempenho ou medições impraticáveis.
3. Se a especificação técnica estiver completa e exequível, retorne um array JSON vazio `[]`.

## FORMATO DE SAÍDA (EXCLUSIVAMENTE JSON):
Retorne um array JSON com objetos no seguinte formato:
```json
[
  {
    "category": "tecnica",
    "severity": "info|baixo|medio|alto|critico",
    "situation": "Situação técnica identificada",
    "problem": "Descrição objetiva da falha técnica ou omissão de requisito",
    "risk": "Risco de inexecução contratual, entrega de material inadequado ou sobrecusto",
    "original_text": "Trecho exato do texto com problema técnico",
    "suggested_text": "Texto corrigido com a especificação técnica adequada",
    "justification": "Justificativa técnica detalhada sobre a melhoria",
    "legal_basis": "Art. 6º, XXIII, 'c' da Lei 14.133/2021 ou Norma Técnica ABNT",
    "importance": "media|alta|critica"
  }
]
```
"""

    def build_user_prompt(self, item: Any, legal_context: str) -> str:
        item_number = getattr(item, "item_number", "1.0")
        item_title = getattr(item, "title", "Item")
        page_number = getattr(item, "page_number", 1)
        item_content = getattr(item, "content", "")

        return f"""AUDITORIA TÉCNICA DO ITEM:

## Dados do Item
- **Número:** {item_number}
- **Título:** {item_title}
- **Página:** {page_number}

## Texto do Item:
{item_content}

Examine sob o aspecto TÉCNICO E OPERACIONAL e retorne o JSON de achados. Se o item estiver tecnicamente perfeito, retorne [].
"""
