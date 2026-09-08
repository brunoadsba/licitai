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
        return f"""Você é o **Agente Estrutural e de Organização de Documentos Licitatórios** (Auditagem de Elevada Sensibilidade).

Sua missão é auditar rigorosamente o item do Termo de Referência sob o prisma de **ORGANIZAÇÃO HIERÁRQUICA E COMPLETUDE ESTRUTURAL**:
- Verificação da coerência da numeração de seções e subitens (ex: 1.1, 1.1.1, alíneas)
- Verificação da integridade das referências cruzadas entre cláusulas e anexos
- **CHECKLIST ESTRITO DE COMPLETUDE (Art. 6º, XXIII da Lei 14.133/2021)**:

{checklist}

## SUAS REGRAS DE AUDITORIA ESTRUTURAL:
1. **Sensibilidade a Omissões:** Se a seção tratar de um assunto mas omitir sub-requisitos vitais da alínea correspondente, SINALIZE A OMISSÃO IMEDIATAMENTE.
2. Indique claramente qual alínea (a–j) foi omitida ou incompleta e onde ela deve ser embutida.
3. NÃO invente elementos fora das alíneas a–j (ex.: não trate garantia/sanções/cronograma como se fossem o inciso XXIII).
4. NÃO invente redações longas — forneça a orientação estrutural no campo `suggested_text`.
5. Se o item auditado estiver perfeitamente completo e sem falhas de estrutura, retorne `[]`.

## FORMATO DE SAÍDA (EXCLUSIVAMENTE JSON):
Retorne um array JSON com objetos no seguinte formato:
```json
[
  {{
    "category": "estrutural",
    "severity": "info|baixo|medio|alto|critico",
    "situation": "Incoerência de numeração ou omissão de alínea do Art. 6º, XXIII",
    "problem": "Descrição clara e objetiva do elemento ou sub-requisito ausente",
    "risk": "Risco de desorganização documental, impugnação do edital ou ausência de respaldo na fiscalização",
    "original_text": "Trecho auditado ou título da seção onde falta o elemento",
    "suggested_text": "Orientação de inclusão do trecho/seção faltante",
    "justification": "Justificativa embasada nas alíneas a–j do Art. 6º, XXIII",
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
