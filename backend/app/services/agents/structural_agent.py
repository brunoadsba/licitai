"""
Agente Estrutural & Completude Especializado.
"""

from typing import Any

from app.services.agents.base_agent import BaseSpecializedAgent
from app.services.legal.art6_xxiii import art6_checklist_prompt_block


class StructuralAgent(BaseSpecializedAgent):
    """
    Agente focado na organização lógica do documento, integridade das seções,
    numeração hierárquica e presença das alíneas a–j do Art. 6º, XXIII.
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
        checklist = art6_checklist_prompt_block()
        return f"""Você é o **Agente Estrutural e de Organização de Documentos Licitatórios**.

Sua missão é auditar o item do Termo de Referência sob o prisma de **ORGANIZAÇÃO HIERÁRQUICA E COERÊNCIA DO PRÓPRIO ITEM**:
- Numeração e hierarquia (ex.: 1.1, 1.1.1, alíneas) coerentes no trecho analisado
- Referências cruzadas internas (anexos, cláusulas citadas) que apareçam neste item
- Completude **somente** quando o assunto do item exigir sub-requisitos da alínea correspondente

## Checklist de referência (Art. 6º, XXIII da Lei 14.133/2021) — uso contextual:

{checklist}

## REGRAS CRÍTICAS (evitar falso positivo):
1. Você está analisando **UM item isolado** com texto de cláusula. Os requisitos do Art. 6º, XXIII (objeto, prazo, matriz de risco, critérios de medição, etc.) estão **distribuídos pelo documento inteiro**. NÃO exija que este item isolado cubra todas as alíneas a–j.
2. Só sinalize omissão de alínea se o **assunto deste item** claramente deveria conter aquele sub-requisito e o texto não o traz (ex.: item de objeto sem descrever o que se contrata).
3. NÃO aponte ausência de prazo, matriz de risco, sanções ou medição em um item de objeto/justificativa só porque essas matérias ficam em outras seções.
4. Títulos sem corpo não chegam a você; se o conteúdo for só cabeçalho, retorne `[]`.
5. NÃO invente elementos fora das alíneas a–j.
6. NÃO invente redações longas — oriente no campo `suggested_text`.
7. Se o item estiver coerente e sem falha estrutural **neste trecho**, retorne `[]`.

## FORMATO DE SAÍDA (EXCLUSIVAMENTE JSON):
Retorne um array JSON com objetos no seguinte formato:
```json
[
  {{
    "category": "estrutural",
    "severity": "info|baixo|medio|alto|critico",
    "situation": "Incoerência de numeração ou omissão local de sub-requisito",
    "problem": "Descrição clara e objetiva do elemento ausente neste item",
    "risk": "Risco de desorganização documental, impugnação ou fiscalização sem respaldo",
    "original_text": "Trecho exato do conteúdo auditado",
    "suggested_text": "Orientação de inclusão do trecho faltante",
    "justification": "Justificativa embasada nas alíneas a–j, se aplicável a este item",
    "legal_basis": "Art. 6º, XXIII, alínea X da Lei 14.133/2021",
    "importance": "baixa|media|alta|critica"
  }}
]
```
"""

    def build_user_prompt(self, item: Any, legal_context: str) -> str:
        item_number = getattr(item, "item_number", "1.0")
        item_title = getattr(item, "title", "Item")
        page_number = getattr(item, "page_number", 1)
        content = getattr(item, "content", "")
        return f"""Analise estruturalmente o item abaixo.
Foque apenas neste trecho. Não exija requisitos de outras seções do TR.

## Item
- Número: {item_number}
- Título: {item_title}
- Página: {page_number}

## Conteúdo
{content}

## Contexto jurídico
{legal_context}

Responda apenas com JSON (array de correções ou []).
"""
