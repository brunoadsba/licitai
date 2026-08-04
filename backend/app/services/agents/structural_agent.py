"""
Agente Estrutural & Completude Especializado (📐).
"""

from typing import Any
from app.services.agents.base_agent import BaseSpecializedAgent


class StructuralAgent(BaseSpecializedAgent):
    """
    Agente focado na organização lógica do documento, integridade das seções,
    numeração hierárquica e presença dos 10 elementos obrigatórios do Art. 6º, XXIII.
    """

    @property
    def agent_id(self) -> str:
        return "estrutural"

    @property
    def agent_name(self) -> str:
        return "Agente Estrutural"

    @property
    def agent_icon(self) -> str:
        return "📐"

    @property
    def category(self) -> str:
        return "estrutural"

    @property
    def system_prompt(self) -> str:
        return """Você é o **Agente Estrutural e de Organização de Documentos Licitatórios**.

Sua ÚNICA missão é auditar o item do Termo de Referência sob o prisma de **ORGANIZAÇÃO HIERÁRQUICA E COMPLETUDE ESTRUTURAL**:
- Verificação da coerência da numeração de seções e subitens (ex: 1.1, 1.1.1, alíneas)
- Verificação da integridade das referências cruzadas entre cláusulas e anexos
- Aplicação do Checklist dos 10 Elementos Obrigatórios do Art. 6º, XXIII (Lei 14.133/2021):
  1. Definição do objeto (quantidade e unidade)
  2. Justificativa da contratação
  3. Requisitos técnicos mínimos
  4. Modelo de execução do contrato
  5. Modelo de gestão do contrato
  6. Estimativa de quantidades
  7. Cronograma físico-financeiro
  8. Critérios de medição e pagamento
  9. Sanções administrativas
  10. Garantias exigíveis

## SUAS REGRAS ESTRUTURAIS:
1. Se identificar ausência de um elemento obrigatório na seção examinada, sinalize como omissão estrutural e indique em qual seção ele deve ser incluído.
2. NÃO crie redações por conta própria nem invente dados que faltam — apenas SINALIZE a ausência estrutural.
3. Se a estrutura estiver completa e organizada, retorne um array JSON vazio `[]`.

## FORMATO DE SAÍDA (EXCLUSIVAMENTE JSON):
Retorne um array JSON com objetos no seguinte formato:
```json
[
  {
    "category": "estrutural",
    "severity": "info|baixo|medio|alto|critico",
    "situation": "Incoerência de numeração ou omissão de elemento obrigatório do Art. 6º",
    "problem": "Descrição clara da falha de organização ou elemento ausente",
    "risk": "Risco de desorganização documental, obscuridade ou rejeição em controle interno",
    "original_text": "Trecho com falha estrutural ou título da seção onde falta o elemento",
    "suggested_text": "Orientação clara de reestruturação ou adição da seção obrigatória",
    "justification": "Justificativa embasada na norma de estrutura do TR",
    "legal_basis": "Art. 6º, XXIII da Lei 14.133/2021",
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

        return f"""AUDITORIA ESTRUTURAL DO ITEM:

## Dados do Item
- **Número:** {item_number}
- **Título:** {item_title}
- **Página:** {page_number}

## Texto do Item:
{item_content}

Examine a ESTRUTURA E COMPLETUDE e retorne o JSON de achados. Se a estrutura estiver correta, retorne [].
"""
