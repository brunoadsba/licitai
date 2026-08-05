"""
Retriever do corpus jurídico (RAG).

Busca os artigos mais relevantes para uma consulta:

- SQLite: índice FTS5 (rank por relevância BM25)
- PostgreSQL: busca por similaridade textual (ILIKE)
- **Semântico (Fase 4):** similaridade de cosseno sobre embeddings
  pré-calculados (coluna `legal_chunks.embedding`), com fallback textual
  automático quando não há embeddings ingeridos ou o provedor falha.

Retorna chunks com a lei, o artigo e o texto integral para o LLM.
"""

import asyncio
import json
import logging
from collections import OrderedDict
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.legal import LegalChunk, LegalDocument
from app.services.embeddings.base import get_embeddings_provider

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
MAX_QUERY_CHARS = 500

_QUERY_EMBEDDING_CACHE: OrderedDict[tuple[str, str], tuple[float, ...]] = OrderedDict()
_QUERY_EMBEDDING_CACHE_MAX = 256
_QUERY_EMBEDDING_LOCK = asyncio.Lock()


def _clear_query_embedding_cache() -> None:
    """Limpa o cache de embeddings de consulta."""
    _QUERY_EMBEDDING_CACHE.clear()


async def _query_embedding_cached(query: str, provider_name: str) -> list[float]:
    """Retorna embedding da query com cache limitado (LRU simples)."""
    key = (query, provider_name)

    async with _QUERY_EMBEDDING_LOCK:
        if key in _QUERY_EMBEDDING_CACHE:
            _QUERY_EMBEDDING_CACHE.move_to_end(key)
            return list(_QUERY_EMBEDDING_CACHE[key])

    provider = get_embeddings_provider()
    vector = await provider.embed(query)

    async with _QUERY_EMBEDDING_LOCK:
        _QUERY_EMBEDDING_CACHE[key] = tuple(vector)
        _QUERY_EMBEDDING_CACHE.move_to_end(key)
        while len(_QUERY_EMBEDDING_CACHE) > _QUERY_EMBEDDING_CACHE_MAX:
            _QUERY_EMBEDDING_CACHE.popitem(last=False)

    return list(vector)


@dataclass
class RetrievedChunk:
    """Chunk recuperado do corpus jurídico."""

    law_number: str
    law_title: str
    article: str
    section: str
    text: str
    score: float


async def retrieve(
    db: AsyncSession,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    law_numbers: list[str] | None = None,
    use_semantic: bool | None = None,
) -> list[RetrievedChunk]:
    """
    Recupera os artigos mais relevantes para a consulta.

    `law_numbers` filtra por lei (ex: ["Lei 14.133/2021"]).

    `use_semantic`: quando None (padrão), decide automaticamente — usa
    busca semântica se houver embeddings ingeridos, senão cai para o
    fallback textual (FTS5/ILIKE), que permanece intacto.
    """
    cleaned = _clean_query(query)
    if not cleaned:
        return []

    if use_semantic is None:
        use_semantic = await _tem_embeddings(db)

    if use_semantic:
        try:
            sem_rows = await _search_semantic(db, cleaned, top_k, law_numbers)
        except Exception:
            logger.exception("Falha na busca semântica; usando fallback textual")
            sem_rows = []

        try:
            text_rows = await _search_textual(db, cleaned, top_k, law_numbers)
        except Exception:
            logger.exception("Falha na busca textual; seguindo apenas com semântica")
            text_rows = []

        rows = _rrf(sem_rows, text_rows, top_k)
        if rows:
            return _para_chunks(rows)

    return _para_chunks(
        await _search_textual(db, cleaned, top_k, law_numbers)
    )


def _rrf(
    sem_rows: list[dict],
    text_rows: list[dict],
    top_k: int,
    k: int = 60,
) -> list[dict]:
    """Combina rankings usando Reciprocal Rank Fusion."""

    def _key(row: dict) -> tuple:
        return (
            row.get("law_number"),
            row.get("article") or "",
            row.get("chunk_text") or "",
        )

    scores: dict[tuple, float] = {}
    merged: dict[tuple, dict] = {}

    for lista in (sem_rows, text_rows):
        for rank, row in enumerate(lista):
            key = _key(row)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            merged.setdefault(key, row)

    ordered = sorted(
        merged.items(),
        key=lambda kv: scores[kv[0]],
        reverse=True,
    )
    return [row for _, row in ordered[:top_k]]


async def _search_textual(
    db: AsyncSession,
    query: str,
    top_k: int,
    law_numbers: list[str] | None,
) -> list[dict]:
    """Executa busca textual respeitando o dialeto do banco."""
    dialect = db.bind.dialect.name if db.bind else "sqlite"
    if dialect == "sqlite":
        return await _search_sqlite(db, query, top_k, law_numbers)
    return await _search_postgres(db, query, top_k, law_numbers)


def _para_chunks(rows: list[dict]) -> list[RetrievedChunk]:
    """Converte linhas de busca em objetos RetrievedChunk."""
    return [
        RetrievedChunk(
            law_number=row["law_number"],
            law_title=row["law_title"],
            article=row["article"] or "",
            section=row["section"] or "",
            text=row["chunk_text"],
            score=float(row["score"]),
        )
        for row in rows
    ]


async def _tem_embeddings(db: AsyncSession) -> bool:
    """Indica se há chunks com embedding armazenado (busca semântica viável)."""
    try:
        result = await db.execute(
            select(func.count()).select_from(LegalChunk).where(
                LegalChunk.embedding.isnot(None),
                LegalChunk.embedding != "",
            )
        )
        return result.scalar_one() > 0
    except Exception:
        logger.exception("Falha ao verificar embeddings no corpus")
        return False


async def _search_semantic(
    db: AsyncSession,
    query: str,
    top_k: int,
    law_numbers: list[str] | None,
) -> list[dict]:
    """Busca por similaridade de cosseno sobre os embeddings armazenados."""
    try:
        provider = get_embeddings_provider()
        query_vector = await _query_embedding_cached(query, provider.provider_name)
    except Exception:
        logger.warning(
            "Embeddings indisponíveis para a consulta; usando fallback textual"
        )
        return []

    if len(query_vector) != settings.embeddings_dim:
        logger.warning(
            "Dimensão da query (%d) difere da configurada (%d). Resultados podem divergir.",
            len(query_vector), settings.embeddings_dim,
        )

    stmt = (
        select(
            LegalChunk,
            LegalDocument.law_number,
            LegalDocument.law_title,
        )
        .join(LegalDocument, LegalDocument.id == LegalChunk.legal_document_id)
        .where(
            LegalChunk.embedding.isnot(None),
            LegalChunk.embedding != "",
        )
    )
    if law_numbers:
        stmt = stmt.where(LegalDocument.law_number.in_(law_numbers))

    result = await db.execute(stmt)
    scored: list[dict] = []
    for chunk, law_number, law_title in result.all():
        try:
            vector = json.loads(chunk.embedding)
        except (TypeError, ValueError):
            continue
        if not vector or len(vector) != len(query_vector):
            continue
        scored.append({
            "law_number": law_number,
            "law_title": law_title,
            "article": chunk.article,
            "section": chunk.section,
            "chunk_text": chunk.chunk_text,
            "score": _cosseno(query_vector, vector),
        })

    scored.sort(key=lambda row: row["score"], reverse=True)
    logger.info(
        "Busca semântica: %d chunks avaliados, retornando top %d",
        len(scored), min(top_k, len(scored)),
    )
    return scored[:top_k]


def _cosseno(a: list[float], b: list[float]) -> float:
    """Similaridade de cosseno entre dois vetores."""
    import math

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def _search_sqlite(
    db: AsyncSession,
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
    db: AsyncSession,
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


def _clean_query(query: str) -> str:
    """Normaliza a consulta para busca (minúsculas, remove ruído)."""
    cleaned = query.strip().lower()[:MAX_QUERY_CHARS]
    return " ".join(cleaned.split())


def _quote_term(term: str) -> str:
    """Escapa um termo para a query FTS5."""
    safe = term.replace('"', "")
    return f'"{safe}"'
