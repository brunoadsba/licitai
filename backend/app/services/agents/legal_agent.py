"""
Agente Jurídico Especializado (⚖️).
"""

from typing import Any
from app.services.agents.base_agent import BaseSpecializedAgent


class LegalAgent(BaseSpecializedAgent):
    """
    Agente focado exclusivamente na segurança jurídica, conformidade normativa
    e mitigação de riscos de impugnação ou nulidade do Termo de Referência.
    """

    @property
    def agent_id(self) -> str:
        return "juridico"

    @property
    def agent_name(self) -> str:
        return "Agente Jurídico"

    @property
    def agent_icon(self) -> str:
        return "⚖️"

    @property
    def category(self) -> str:
        return "juridica"

    @property
    def system_prompt(self) -> str:
        return """Você é o **Agente Jurídico Especialista em Licitações Públicas**, atuando como Consultor Jurídico Sênior (Advocacia Pública/AGU).

Sua ÚNICA missão é auditar o item do Termo de Referência sob o prisma de **CONFORMIDADE LEGAL E JURISPRUDENCIAL**:
- Lei 14.133/2021 (Nova Lei de Licitações e Contratos)
- Lei 13.303/2016 (Lei das Estatais)
- Súmulas e Acórdãos do Tribunal de Contas da União (TCU)
- Pareceres Referenciais da Advocacia-Geral da União (AGU) e CGU

## SUAS REGRAS E LIMITES JURÍDICOS:
1. Examine se há ausência de amparo legal, exigências ilegais de habilitação, critérios de julgamento vedados, sanções desproporcionais ou riscos de representação ao órgão de controle.
2. CITE SEMPRE a fundamentação jurídica exata (Artigo, Inciso, Alínea da Lei ou Número do Acórdão TCU). NUNCA invente leis.
3. Se não houver infração legal ou risco jurídico no item, retorne um array JSON vazio `[]`.

## FORMATO DE SAÍDA (EXCLUSIVAMENTE JSON):
Retorne um array JSON com objetos no seguinte formato:
```json
[
  {
    "category": "juridica",
    "severity": "info|baixo|medio|alto|critico",
    "situation": "Situação jurídica identificada",
    "problem": "Descrição clara do vício legal ou risco jurídico",
    "risk": "Risco de impugnação do edital, anulação ou sanção pelo TCU",
    "original_text": "Trecho exato do texto original com o vício legal",
    "suggested_text": "Texto corrigido em conformidade jurídica",
    "justification": "Explicação fundamentada sobre o ajuste legal",
    "legal_basis": "Art. XX da Lei 14.133/2021 ou Acórdão XX do TCU",
    "importance": "alta|critica"
  }
]
```
"""

    def build_user_prompt(self, item: Any, legal_context: str) -> str:
        item_number = getattr(item, "item_number", "1.0")
        item_title = getattr(item, "title", "Item")
        page_number = getattr(item, "page_number", 1)
        item_content = getattr(item, "content", "")

        return f"""AUDITORIA JURÍDICA DO ITEM:

## Dados do Item
- **Número:** {item_number}
- **Título:** {item_title}
- **Página:** {page_number}

## Texto do Item:
{item_content}

## Base Jurídica de Referência (RAG):
{legal_context if legal_context else "Usar jurisprudência padrão da Lei 14.133/21 e TCU."}

Examine minuciosamente sob o aspecto JURÍDICO e retorne o JSON de achados. Se estiver em conformidade legal, retorne [].
"""
