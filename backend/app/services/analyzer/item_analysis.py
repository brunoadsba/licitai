"""
Análise de item individual via LLM (prompt + parsing de correções).

Extraído do antigo engine.py para separar a responsabilidade de orquestração
(engine) da análise unitária reutilizável (benchmark usa com contexto fixo).
"""

import logging

from app.services.analyzer.json_utils import (
    parse_json_response,
    sanitize_correction,
    validate_correction,
)
from app.services.analyzer.prompts import ITEM_ANALYSIS_PROMPT, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

ITEM_CONTENT_MAX_CHARS = 8000


async def analyze_item_llm(llm, item, legal_context: str) -> list[dict]:
    """Analisa um item via LLM usando contexto jurídico fornecido (sem DB).

    Usada pelo engine (com contexto do RAG) e pelo benchmark (com contexto fixo).
    """
    content = item.content or ""
    if len(content) > ITEM_CONTENT_MAX_CHARS:
        logger.warning(
            "Item %s truncado de %d para %d chars no prompt",
            item.item_number, len(content), ITEM_CONTENT_MAX_CHARS,
        )
        content = content[:ITEM_CONTENT_MAX_CHARS]

    user_prompt = ITEM_ANALYSIS_PROMPT.format(
        item_number=item.item_number,
        item_title=item.title or "(sem título)",
        page_number=item.page_number or "N/A",
        item_content=content,
        legal_context=legal_context,
    )

    response = await llm.generate(SYSTEM_PROMPT, user_prompt)

    # Parsear resposta JSON
    corrections = parse_json_response(response)

    # Validar e limpar cada correção
    valid_corrections = []
    for c in corrections:
        if isinstance(c, dict) and validate_correction(c):
            valid_corrections.append(sanitize_correction(c))

    return valid_corrections