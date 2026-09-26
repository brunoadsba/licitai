"""
Análise de item individual via LLM (prompt + parsing de correções).

Extraído do antigo engine.py para separar a responsabilidade de orquestração
(engine) da análise unitária reutilizável (benchmark usa com contexto fixo).
"""

import logging

from app.services.analyzer.batching import (
    BATCH_ATTRIBUTION_INSTRUCTION,
    batch_numbers_label,
    split_corrections_by_item,
)
from app.services.analyzer.json_utils import (
    parse_json_response,
    sanitize_correction,
    validate_correction,
)
from app.services.analyzer.prompts import ITEM_ANALYSIS_PROMPT, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

ITEM_CONTENT_MAX_CHARS = 4000
ITEM_SUMMARY_CHARS = 800


async def analyze_item_llm(
    llm, item, legal_context: str, document_facts: str = ""
) -> list[dict]:
    """Analisa um item via LLM usando contexto jurídico fornecido (sem DB).

    Usada pelo engine (com contexto do RAG) e pelo benchmark (com contexto fixo).
    `document_facts` vazio no benchmark: o quadro do TR não é injetado.
    """
    content = item.content or ""
    if len(content) > ITEM_CONTENT_MAX_CHARS:
        head = content[: ITEM_CONTENT_MAX_CHARS - ITEM_SUMMARY_CHARS]
        tail = content[-ITEM_SUMMARY_CHARS:]
        content = f"{head}\n[...conteúdo resumido: {len(content) - ITEM_CONTENT_MAX_CHARS} chars omitidos...]\n{tail}"
        logger.warning(
            "Item %s comprimido de %d para ~%d chars no prompt",
            item.item_number,
            len(item.content or ""),
            len(content),
        )

    user_prompt = ITEM_ANALYSIS_PROMPT.format(
        item_number=item.item_number,
        item_title=item.title or "(sem título)",
        page_number=item.page_number or "N/A",
        item_content=content,
        legal_context=legal_context,
        document_facts=document_facts,
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


def _format_batch_section(item, legal_context: str, document_facts: str = "") -> str:
    """Monta a seção de um item no prompt em lote (mesmo prompt unitário)."""
    content = item.content or ""
    if len(content) > ITEM_CONTENT_MAX_CHARS:
        head = content[: ITEM_CONTENT_MAX_CHARS - ITEM_SUMMARY_CHARS]
        tail = content[-ITEM_SUMMARY_CHARS:]
        content = f"{head}\n[...conteúdo resumido: {len(content) - ITEM_CONTENT_MAX_CHARS} chars omitidos...]\n{tail}"
    return (
        f"=== ITEM {getattr(item, 'item_number', '?')} ===\n"
        + ITEM_ANALYSIS_PROMPT.format(
            item_number=getattr(item, "item_number", "?"),
            item_title=getattr(item, "title", None) or "(sem título)",
            page_number=getattr(item, "page_number", None) or "N/A",
            item_content=content,
            legal_context=legal_context,
            document_facts=document_facts,
        )
    )


async def analyze_batch_llm(
    llm, batch: list[tuple], document_facts: str = ""
) -> dict[str, list[dict]]:
    """Analisa um lote de (item, contexto) em UMA chamada LLM (modo single).

    Cada correção precisa carregar `item_number` válido do lote; atribuição
    desconhecida é descartada (fail-closed), nunca remapeada.
    """
    numbers = batch_numbers_label(batch)
    user_prompt = (
        BATCH_ATTRIBUTION_INSTRUCTION.format(n=len(batch), numbers=numbers)
        + "\n\n"
        + "\n\n".join(
            _format_batch_section(item, ctx, document_facts) for item, ctx in batch
        )
    )

    response = await llm.generate(SYSTEM_PROMPT, user_prompt)
    corrections = parse_json_response(response)
    if isinstance(corrections, dict):
        corrections = [corrections]
    if not isinstance(corrections, list):
        corrections = []

    valid = [
        c for c in corrections if isinstance(c, dict) and validate_correction(c)
    ]
    routed = split_corrections_by_item(batch, valid)
    return {
        str(item.id): [sanitize_correction(c) for c in routed[str(item.id)]]
        for item, _ in batch
    }