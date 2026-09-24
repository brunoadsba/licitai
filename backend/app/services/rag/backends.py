"""
Backends de busca textual por dialeto do banco.

SQLite usa índice FTS5 com ranking BM25; PostgreSQL usa FTS (tsvector).
"""

from sqlalchemy import text

from app.services.rag.published import apply_sql_published_filter
from app.services.rag.quarantine import apply_sql_quarantine_filter


async def _search_textual(
    db,
    query: str,
    top_k: int,
    law_numbers: list[str] | None,
    exclude_quarantine: bool = True,
) -> list[dict]:
    """Executa busca textual respeitando o dialeto do banco."""
    dialect = db.bind.dialect.name if db.bind else "sqlite"
    if dialect == "sqlite":
        return await _search_sqlite(
            db, query, top_k, law_numbers, exclude_quarantine
        )
    return await _search_postgres(
        db, query, top_k, law_numbers, exclude_quarantine
    )


def _postgres_or_tsquery(query: str) -> str:
    from app.services.rag.query_terms import postgres_tsquery

    return postgres_tsquery(query, "or")


_STOPWORDS_PT = frozenset({
    "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas",
    "por", "para", "com", "sem", "sob", "sobre", "que", "os", "as", "o", "a",
    "um", "uma", "uns", "umas", "ao", "aos", "se", "como", "ou", "é", "são",
})


def _quote_term(term: str) -> str:
    """Escapa um termo para a query FTS5."""
    safe = term.replace('"', "")
    return f'"{safe}"'


def _fts_terms(query: str) -> list[str]:
    """Termos FTS5: sem stopwords PT; prefixo `*` em termos longos (stemming pobre).

    "estatal"* casa "estatais"; "por"/"de" saem (poluíam o BM25 casando tudo).
    """
    terms = []
    for t in query.split():
        low = t.lower()
        if low in _STOPWORDS_PT:
            continue
        if len(low) >= 5:
            terms.append(f'{_quote_term(t)}*')
        else:
            terms.append(_quote_term(t))
    return terms or [_quote_term(query)]


async def _search_sqlite(
    db,
    query: str,
    top_k: int,
    law_numbers: list[str] | None,
    exclude_quarantine: bool = True,
) -> list[dict]:
    """Busca por FTS5 com ranking BM25 e consulta direta por artigo."""
    match_expr = " OR ".join(_fts_terms(query))
    base_sql = """
        SELECT CAST(lc.id AS TEXT) AS id, ld.law_number, ld.law_title, lc.article, lc.section,
               lc.chunk_text, ld.version, bm25(legal_chunks_fts) AS score
        FROM legal_chunks_fts
        JOIN legal_chunks lc ON CAST(lc.id AS TEXT) = legal_chunks_fts.chunk_id
        JOIN legal_documents ld ON ld.id = lc.legal_document_id
        WHERE legal_chunks_fts MATCH :match
    """
    params = {"match": match_expr}
    if exclude_quarantine:
        base_sql = apply_sql_quarantine_filter(base_sql, params)
    base_sql = apply_sql_published_filter(base_sql)

    if law_numbers:
        placeholders = ", ".join(f":law{i}" for i in range(len(law_numbers)))
        base_sql += f" AND ld.law_number IN ({placeholders})"
        params.update({f"law{i}": law for i, law in enumerate(law_numbers)})

    base_sql += " ORDER BY score LIMIT :limit"
    params["limit"] = top_k

    result = await db.execute(text(base_sql), params)
    rows = [dict(row._mapping) for row in result.fetchall()]
    from app.services.rag.article_query import (
        article_like,
        merge_article_hits,
        search_article_column,
    )

    art_like = article_like(query)
    if art_like:
        extra = await search_article_column(
            db, art_like, top_k, law_numbers, exclude_quarantine
        )
        rows = merge_article_hits(extra, rows, top_k)
    return rows


async def _search_postgres(
    db,
    query: str,
    top_k: int,
    law_numbers: list[str] | None,
    exclude_quarantine: bool = True,
) -> list[dict]:
    """FTS português com ranking; artigo direto; ILIKE só se o índice FTS faltar."""
    from app.services.rag.article_query import article_like

    from app.services.rag.article_query import filter_weak_fts_hits, merge_article_hits
    from app.services.rag.query_terms import postgres_tsquery

    art_like = article_like(query)
    merged: list[dict] = []
    for mode in ("and", "or"):
        fts_q = postgres_tsquery(query, mode)
        params: dict = {"q": fts_q, "limit": top_k, "art_like": art_like or ""}
        sql = """
        SELECT CAST(lc.id AS TEXT) AS id, ld.law_number, ld.law_title, lc.article,
               lc.section, lc.chunk_text, ld.version,
               ts_rank_cd(lc.search_tsv, query) AS score
        FROM legal_chunks lc
        JOIN legal_documents ld ON ld.id = lc.legal_document_id
        , to_tsquery('portuguese', licitai_unaccent(:q)) query
        WHERE (
            lc.search_tsv @@ query
            OR (:art_like <> '' AND lc.article ILIKE :art_like)
        )
        """
        if exclude_quarantine:
            sql = apply_sql_quarantine_filter(sql, params)
        sql = apply_sql_published_filter(sql)
        if law_numbers:
            placeholders = ", ".join(f":law{i}" for i in range(len(law_numbers)))
            sql += f" AND ld.law_number IN ({placeholders})"
            params.update({f"law{i}": law for i, law in enumerate(law_numbers)})
        sql += " ORDER BY score DESC NULLS LAST LIMIT :limit"
        try:
            result = await db.execute(text(sql), params)
            rows = filter_weak_fts_hits(
                query, [dict(row._mapping) for row in result.fetchall()]
            )
            merged = merge_article_hits(merged, rows, top_k)
        except Exception:
            continue
    if merged:
        return merged
    return await _search_postgres_ilike(
        db, query, top_k, law_numbers, exclude_quarantine
    )


async def _search_postgres_ilike(
    db,
    query: str,
    top_k: int,
    law_numbers: list[str] | None,
    exclude_quarantine: bool,
) -> list[dict]:
    """Fallback legado se search_tsv ainda não existir."""
    terms = [f"%{t}%".replace("'", "") for t in query.split()[:6]]
    conditions = " OR ".join(f"lc.chunk_text ILIKE :term{i}" for i in range(len(terms)))
    params = {f"term{i}": t for i, t in enumerate(terms)}
    sql = f"""
        SELECT CAST(lc.id AS TEXT) AS id, ld.law_number, ld.law_title, lc.article,
               lc.section, lc.chunk_text, ld.version, 1 AS score
        FROM legal_chunks lc
        JOIN legal_documents ld ON ld.id = lc.legal_document_id
        WHERE {conditions}
    """
    if exclude_quarantine:
        sql = apply_sql_quarantine_filter(sql, params)
    sql = apply_sql_published_filter(sql)
    if law_numbers:
        placeholders = ", ".join(f":law{i}" for i in range(len(law_numbers)))
        sql += f" AND ld.law_number IN ({placeholders})"
        params.update({f"law{i}": law for i, law in enumerate(law_numbers)})
    sql += " LIMIT :limit"
    params["limit"] = top_k
    result = await db.execute(text(sql), params)
    return [dict(row._mapping) for row in result.fetchall()]
