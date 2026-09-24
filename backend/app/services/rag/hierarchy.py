"""Expande chunks com caput/ancestrais sem cortar o fim do artigo."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_versioned import LegalIdMap, LegalProvision, LegalWork
from app.services.legal_model.provisions import _norm_art
from app.services.legal_model.query import ancestors_and_related

_CHARS_PER_TOKEN = 4
DEFAULT_TOKEN_BUDGET = 1800


def _tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


async def expand_hierarchical(
    db: AsyncSession,
    chunks: list,
    *,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> list:
    """Prefere menos dispositivos a truncar um artigo no meio."""
    from app.services.rag.retriever import RetrievedChunk

    if not chunks:
        return []
    expanded: list = []
    used = 0
    for chunk in chunks:
        text = await _with_ancestors(db, chunk)
        cost = _tokens(text)
        if expanded and used + cost > token_budget:
            break
        expanded.append(
            RetrievedChunk(
                id=chunk.id,
                law_number=chunk.law_number,
                law_title=chunk.law_title,
                article=chunk.article,
                section=chunk.section,
                text=text,
                score=chunk.score,
            )
        )
        used += cost
    return expanded


def provision_path_from_article(article: str | None) -> str | None:
    if not article:
        return None
    match = re.search(r"(\d+[º°\-A-Za-z]*)", article)
    if not match:
        return None
    return f"art.{_norm_art(match.group(1))}"


async def _with_ancestors(db: AsyncSession, chunk) -> str:
    provision = await _resolve_provision(db, chunk)
    if not provision:
        return chunk.text
    chain = await ancestors_and_related(db, provision)
    parts = [p.canonical_text for p in chain if p.canonical_text not in chunk.text]
    if not parts:
        return chunk.text
    return "\n\n".join([*parts, chunk.text])


async def _resolve_provision(db: AsyncSession, chunk):
    chunk_id = getattr(chunk, "id", None)
    if chunk_id:
        try:
            mapped_id = uuid.UUID(str(chunk_id))
        except (TypeError, ValueError):
            mapped_id = None
        if mapped_id is not None:
            mapped = (
                await db.execute(
                    select(LegalProvision)
                    .join(LegalIdMap, LegalIdMap.provision_id == LegalProvision.id)
                    .where(LegalIdMap.old_chunk_id == mapped_id)
                )
            ).scalar_one_or_none()
            if mapped:
                return mapped
    work = (
        await db.execute(
            select(LegalWork).where(LegalWork.law_number == chunk.law_number)
        )
    ).scalar_one_or_none()
    path = provision_path_from_article(chunk.article)
    if not work or not path:
        return None
    return (
        await db.execute(
            select(LegalProvision).where(
                LegalProvision.work_id == work.id,
                LegalProvision.path == path,
                LegalProvision.status == "vigente",
            )
        )
    ).scalar_one_or_none()
