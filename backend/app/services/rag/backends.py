"""
Backends de busca textual por dialeto do banco.

SQLite usa índice FTS5 com ranking BM25; PostgreSQL usa ILIKE.
"""

from sqlalchemy import text


async def _search_textual(
    db,
    query: str,
    top_k: int,
    law_numbers: list[str] | None,
) -> list[dict]:
    """Executa busca textual respeitando o dialeto do banco."""
    dialect = db.bind.dialect.name if db.bind else "sqlite"
    if dialect == "sqlite":
        return await _search_sqlite(db, query, top_k, law_numbers)
    return await _search_postgres(db, query, top_k, law_numbers)


def _quote_term(term: str) -> str:
    """Escapa um termo para a query FTS5."""
    safe = term.replace('"', "")
    return f'"{safe}"'


async def _search_sqlite(
    db,
    query: str,
    top_k: int,
    law_numbers: list[str] | None,
) -> list[dict]:
    """Busca por FTS5 com ranking BM25."""
    match_expr = " OR ".join(_quote_term(t) for t in query.split())

    base_sql = """
        SELECT ld.law_number, ld.law_title, lc.article, lc.section,
               lc.chunk_text, bm25(legal_chunks_fts) AS score
        FROM legal_chunks_fts
        JOIN legal_chunks lc ON CAST(lc.id AS TEXT) = legal_chunks_fts.chunk_id
        JOIN legal_documents ld ON ld.id = lc.legal_document_id
        WHERE legal_chunks_fts MATCH :match
    """
    params = {"match": match_expr}

    if law_numbers:
        placeholders = ", ".join(f":law{i}" for i in range(len(law_numbers)))
        base_sql += f" AND ld.law_number IN ({placeholders})"
        params.update({f"law{i}": law for i, law in enumerate(law_numbers)})

    base_sql += " ORDER BY score LIMIT :limit"
    params["limit"] = top_k

    result = await db.execute(text(base_sql), params)
    return [dict(row._mapping) for row in result.fetchall()]


async def _search_postgres(
    db,
    query: str,
    top_k: int,
    law_numbers: list[str] | None,
) -> list[dict]:
    """Busca por similaridade textual (ILIKE) em PostgreSQL."""
    terms = [f"%{t}%".replace("'", "") for t in query.split()[:6]]
    conditions = " OR ".join(f"lc.chunk_text ILIKE :term{i}" for i in range(len(terms)))
    params = {f"term{i}": t for i, t in enumerate(terms)}

    sql = f"""
        SELECT ld.law_number, ld.law_title, lc.article, lc.section,
               lc.chunk_text, 1 AS score
        FROM legal_chunks lc
        JOIN legal_documents ld ON ld.id = lc.legal_document_id
        WHERE {conditions}
    """

    if law_numbers:
        placeholders = ", ".join(f":law{i}" for i in range(len(law_numbers)))
        sql += f" AND ld.law_number IN ({placeholders})"
        params.update({f"law{i}": law for i, law in enumerate(law_numbers)})

    sql += " LIMIT :limit"
    params["limit"] = top_k

    result = await db.execute(text(sql), params)
    return [dict(row._mapping) for row in result.fetchall()]
