"""Itens do TR que batem com a pergunta, além do item que está aberto na tela."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentItem
from app.schemas.chat import ChatCitation
from app.services.chat.relevance import lexical_score

logger = logging.getLogger(__name__)

_ITEM_CAP = 3
_SNIPPET = 700


async def matching_document_items(
    db: AsyncSession,
    document_id: str | None,
    query: str,
    focused_item_number: str | None,
) -> list[ChatCitation]:
    if not document_id:
        return []

    async def _buscar():
        result = await db.execute(
            select(DocumentItem).where(
                DocumentItem.document_id == document_id,
                DocumentItem.archived_at.is_(None),
            )
        )
        return result.scalars().all()

    itens = await _buscar_seguro(db, _buscar)
    citados: list[tuple[int, ChatCitation]] = []
    for item in itens:
        if item is None:
            continue
        if item.item_type == "table" and "tabela" not in (query or "").lower():
            continue
        texto = f"{item.item_number} {item.title or ''} {item.content or ''}"
        pontos = lexical_score(query, texto)
        focado = (
            focused_item_number is not None
            and str(item.item_number) == str(focused_item_number)
        )
        if pontos <= 0 and not focado:
            continue
        citados.append((pontos + (2 if focado else 0), _citation(document_id, item)))

    citados.sort(key=lambda par: par[0], reverse=True)
    return [cit for _, cit in citados[:_ITEM_CAP]]


def _citation(document_id: str, item: DocumentItem) -> ChatCitation:
    return ChatCitation(
        type="document_item",
        source_id=f"doc:{document_id}:item:{item.item_number}",
        reference=f"Item {item.item_number}",
        title=item.title or "Item do documento",
        snippet=_recorte(item.content),
    )


def _recorte(texto: str) -> str:
    texto = (texto or "").strip().replace("\n", " ")
    return texto[:_SNIPPET]


async def _buscar_seguro(db: AsyncSession, operacao) -> list:
    try:
        async with db.begin_nested():
            return list(await operacao())
    except Exception:
        logger.exception("Falha ao buscar itens do TR para o copiloto")
        return []
