"""Detecta consulta direta por artigo e busca por coluna."""

from __future__ import annotations

import re

from sqlalchemy import text

from app.services.rag.published import apply_sql_published_filter
from app.services.rag.quarantine import apply_sql_quarantine_filter

_ARTICLE_QUERY_RE = re.compile(
    r"\b(?:art(?:igo)?\.?)\s*(\d+[a-z]?)(?:[º°])?",
    re.IGNORECASE,
)


def extract_article_ref(query: str) -> str | None:
    match = _ARTICLE_QUERY_RE.search(query or "")
    if not match:
        return None
    return match.group(1)


def article_like(query: str) -> str | None:
    ref = extract_article_ref(query)
    if not ref:
        return None
    return f"%{ref}%"


async def search_article_column(
    db,
    art_like: str,
    top_k: int,
    law_numbers: list[str] | None,
    exclude_quarantine: bool,
) -> list[dict]:
    sql = """
        SELECT CAST(lc.id AS TEXT) AS id, ld.law_number, ld.law_title, lc.article,
               lc.section, lc.chunk_text, ld.version, 0.0 AS score
        FROM legal_chunks lc
        JOIN legal_documents ld ON ld.id = lc.legal_document_id
        WHERE lc.article LIKE :art_like
    """
    params: dict = {"art_like": art_like, "limit": top_k}
    if exclude_quarantine:
        sql = apply_sql_quarantine_filter(sql, params)
    sql = apply_sql_published_filter(sql)
    if law_numbers:
        placeholders = ", ".join(f":law{i}" for i in range(len(law_numbers)))
        sql += f" AND ld.law_number IN ({placeholders})"
        params.update({f"law{i}": law for i, law in enumerate(law_numbers)})
    sql += " LIMIT :limit"
    result = await db.execute(text(sql), params)
    return [dict(row._mapping) for row in result.fetchall()]


def merge_article_hits(
    article_rows: list[dict], fts_rows: list[dict], top_k: int
) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []
    for row in [*article_rows, *fts_rows]:
        key = str(row.get("id") or "")
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
        if len(merged) >= top_k:
            break
    return merged


def filter_weak_fts_hits(query: str, rows: list[dict]) -> list[dict]:
    """Descarta hit fraco; ignora 'lei'/'14.133' que estão em quase todo o corpus."""
    from app.services.rag.query_terms import content_terms, fold

    terms = [t for t in content_terms(query) if len(t) >= 3]
    if len(terms) < 3 or not rows:
        return rows
    kept: list[dict] = []
    for row in rows:
        hay = fold(f"{row.get('chunk_text') or ''} {row.get('article') or ''}")
        hits = sum(1 for t in terms if t in hay)
        if hits >= 2:
            kept.append(row)
    return kept
