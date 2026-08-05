"""
Montagem das fontes citadas nas respostas do Copiloto.

Toda resposta factual exige citação válida de fonte. As fontes são:

- `legal`: artigos do corpus jurídico recuperados pelo RAG (`retrieve`).
- `analysis`: parecer/resultados de uma análise do documento.
- `correction`: correções apontadas pela análise.
- `document_item`: item específico do documento referenciado no contexto.

Falhas de recuperação são tratadas individualmente (nunca derrubam a
resposta): se nada for recuperado, a resposta fica sem citação e o validator
decide entre recusar (grounding obrigatório) ou responder com warning.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.analysis import Analysis, Correction
from app.models.document import DocumentItem
from app.schemas.chat import ChatCitation
from app.services.rag.retriever import retrieve


logger = logging.getLogger(__name__)

_SNIPPET_MAX = 400


def _snippet(texto: str) -> str:
    texto = (texto or "").strip().replace("\n", " ")
    return texto[:_SNIPPET_MAX]


async def _seguro(db: AsyncSession, operacao) -> list:
    """
    Executa uma operação de recuperação dentro de um savepoint.

    Falhas de consulta (ex: tabela FTS ausente em banco vazio) não podem
    envenenar a transação principal da conversa — o savepoint é revertido
    e a operação retorna lista vazia.
    """
    try:
        async with db.begin_nested():
            resultado = await operacao()
            return list(resultado)
    except Exception:
        logger.exception("Falha ao recuperar fontes do copiloto")
        return []


async def _legal_sources(db: AsyncSession, query: str) -> list[ChatCitation]:
    async def _buscar():
        return await retrieve(
            db,
            query,
            top_k=settings.chat_top_k_sources,
        )

    chunks = await _seguro(db, _buscar)

    return [
        ChatCitation(
            type="legal",
            reference=f"{c.law_number}, {c.article}".rstrip(", "),
            title=c.law_title,
            snippet=_snippet(c.text),
        )
        for c in chunks
    ]


async def _analysis_sources(
    db: AsyncSession, analysis_id: str | None
) -> list[ChatCitation]:
    if not analysis_id:
        return []

    async def _buscar():
        return [await db.get(Analysis, analysis_id)]

    analysis = await _seguro(db, _buscar)
    analysis = analysis[0] if analysis else None
    if not analysis:
        return []
    return [
        ChatCitation(
            type="analysis",
            reference=f"Análise {analysis_id}",
            title="Análise do documento",
            snippet=_snippet(
                analysis.final_opinion
                or f"Status: {analysis.status} · Nota geral: {analysis.score_overall}"
            ),
        )
    ]


async def _correction_sources(
    db: AsyncSession, analysis_id: str | None, limit: int
) -> list[ChatCitation]:
    if not analysis_id:
        return []

    async def _buscar():
        result = await db.execute(
            select(Correction)
            .where(Correction.analysis_id == analysis_id)
            .limit(limit)
        )
        return result.scalars().all()

    corrections = await _seguro(db, _buscar)
    return [
        ChatCitation(
            type="correction",
            reference=f"Correção · {c.category} · {c.severity}",
            title=c.problem,
            snippet=_snippet(c.suggested_text or c.justification),
        )
        for c in corrections
    ]


async def _document_item_sources(
    db: AsyncSession,
    document_id: str | None,
    item_number: str | None,
) -> list[ChatCitation]:
    if not document_id or not item_number:
        return []

    async def _buscar():
        result = await db.execute(
            select(DocumentItem).where(
                DocumentItem.document_id == document_id,
                DocumentItem.item_number == item_number,
            )
        )
        return [result.scalar_one_or_none()]

    item = await _seguro(db, _buscar)
    item = item[0] if item else None
    if not item:
        return []
    return [
        ChatCitation(
            type="document_item",
            reference=f"Item {item.item_number}",
            title=item.title or "Item do documento",
            snippet=_snippet(item.content),
        )
    ]


def _dedupe(fontes: list[ChatCitation]) -> list[ChatCitation]:
    vistos: set[tuple[str, str]] = set()
    resultado: list[ChatCitation] = []
    for f in fontes:
        chave = (f.type, f.reference)
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(f)
    return resultado


async def build_sources(
    db: AsyncSession,
    query: str,
    context: dict | None,
) -> list[ChatCitation]:
    """Monta as fontes citáveis da resposta, deduplicadas e limitadas."""
    context = context or {}
    fontes: list[ChatCitation] = []

    fontes.extend(await _legal_sources(db, query))

    analysis_id = context.get("analysis_id") or context.get("analysisId")
    document_id = context.get("document_id") or context.get("documentId")
    item_number = context.get("item_number")

    if analysis_id:
        fontes.extend(await _analysis_sources(db, str(analysis_id)))
        fontes.extend(
            await _correction_sources(
                db, str(analysis_id), settings.chat_max_sources_stored
            )
        )

    if document_id:
        fontes.extend(
            await _document_item_sources(
                db, str(document_id), str(item_number) if item_number else None
            )
        )

    return _dedupe(fontes)[: settings.chat_max_sources_stored]
