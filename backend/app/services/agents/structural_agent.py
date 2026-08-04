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
        return """Você é o **Agente Estrutural e de Organização de Documentos Licitatórios** (Auditagem de Elevada Sensibilidade).

Sua missão é auditar rigorosamente o item do Termo de Referência sob o prisma de **ORGANIZAÇÃO HIERÁRQUICA E COMPLETUDE ESTRUTURAL**:
- Verificação da coerência da numeração de seções e subitens (ex: 1.1, 1.1.1, alíneas)
- Verificação da integridade das referências cruzadas entre cláusulas e anexos
- **CHECKLIST ESTRITO DE COMPLETUDE (Art. 6º, XXIII da Lei 14.133/2021)**:
  1. **Objeto:** Definição clara, quantitativos precisos e unidades de medida.
  2. **Justificativa:** Fundamentação da necessidade da contratação e alinhamento estratégico.
  3. **Especificação Técnica:** Requisitos mínimos, normas ABNT e parâmetros de qualidade sem direcionamento.
  4. **Modelo de Execução:** Prazos de entrega/início, locais, amostragem e procedimentos operacionais.
  5. **Modelo de Gestão e Fiscalização:** Procedimentos de recebimento provisório/definitivo e papel do fiscal.
  6. **Critérios de Medição e Pagamento:** Indicadores de desempenho (SLA), liquidação e prazo de pagamento.
  7. **Estimativa de Preços / Adequação Orçamentária:** Metodologia de pesquisa ou indicação de dotação.
  8. **Garantia Contratual / Assistência Técnica:** Percentuais, modalidades aceitas e cobertura.
  9. **Infrações e Sanções Administrativas:** Gradação de penalidades e prazo de defesa prévia.
  10. **Forma de Seleção e Critério de Julgamento:** Tipo de licitação e critérios objetivo de avaliação.

## SUAS REGRAS DE AUDITORIA ESTRUTURAL:
1. **Sensibilidade a Omissões:** Se a seção tratar de um assunto mas omitir sub-requisitos vitais (ex: falar de pagamento sem fixar o prazo de liquidação; falar de sanções sem citar a ampla defesa; omitir amostragem onde aplicável), SINALIZE A OMISSÃO IMEDIATAMENTE.
2. Indique claramente qual o elemento omitido ou incompleto e onde ele deve ser embutido.
3. NÃO invente redações longas — forneça a orientação estrutural no campo `suggested_text`.
4. Se o item auditado estiver perfeitamente completo e sem falhas de estrutura, retorne `[]`.

## FORMATO DE SAÍDA (EXCLUSIVAMENTE JSON):
Retorne um array JSON com objetos no seguinte formato:
```json
[
  {
    "category": "estrutural",
    "severity": "info|baixo|medio|alto|critico",
    "situation": "Incoerência de numeração ou omissão de elemento obrigatório do Art. 6º, XXIII",
    "problem": "Descrição clara e objetiva do elemento ou sub-requisito ausente",
    "risk": "Risco de desorganização documental, impugnação do edital ou ausência de respaldo na fiscalização",
    "original_text": "Trecho auditado ou título da seção onde falta o elemento",
    "suggested_text": "Orientação de inclusão do trecho/seção faltante",
    "justification": "Justificativa embasada nas normas de completude de TR",
    "legal_basis": "Art. 6º, XXIII da Lei 14.133/2021",
    "importance": "baixa|media|alta|critica"
  }
]
```
"""

    def build_user_prompt(self, item: Any, legal_context: str) -> str:
        item_number = getattr(item, "item_number", "1.0")
        item_title = getattr(item, "title", "Item")
        page_number = getattr(item, "page_number", 1)
        item_content = getattr(item, "content", "")

        return f"""AUDITORIA ESTRUTURAL E DE COMPLETUDE DO ITEM:

## Dados do Item
- **Número:** {item_number}
- **Título:** {item_title}
- **Página:** {page_number}

## Texto do Item:
{item_content}

## Contexto Legal Relevante:
{legal_context if legal_context else "Sem contexto adicional."}

Examine a ESTRUTURA E COMPLETUDE ESTRITA sob o Art. 6º, XXIII e retorne o JSON de achados. Se não houver falhas nem omissões, retorne [].
"""
