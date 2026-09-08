"""
Busca semântica sobre embeddings do corpus jurídico.

Preferência:
1. Postgres + coluna embedding_vector preenchida → distância cosseno pgvector (`<=>`)
2. Fallback: embeddings JSON em `embedding` + cosseno em Python

Bloqueia query se dimensão incompatível com settings.embeddings_dim /
chunk.embedding_dim.
"""

from __future__ import annotations

import json
import logging
from collections import OrderedDict

from sqlalchemy import func, select, text

from app.config import settings
from app.models.legal import LegalChunk, LegalDocument

logger = logging.getLogger(__name__)

_QUERY_EMBEDDING_CACHE: OrderedDict[tuple[str, str], tuple[float, ...]] = OrderedDict()
_QUERY_EMBEDDING_CACHE_MAX = 256


class EmbeddingDimensionError(ValueError):
    """Dimensão do embedding da query incompatível com o corpus/config."""


def _clear_query_embedding_cache() -> None:
    """Limpa o cache de embeddings de consulta."""
    _QUERY_EMBEDDING_CACHE.clear()


async def _query_embedding_cached(query: str, provider_name: str) -> list[float]:
    """Retorna embedding da query com cache limitado (LRU simples)."""
    key = (query, provider_name)

    cached = _QUERY_EMBEDDING_CACHE.get(key)
    if cached is not None:
        _QUERY_EMBEDDING_CACHE.move_to_end(key)
        return list(cached)

    import app.services.rag.retriever as retriever_module

    provider = retriever_module.get_embeddings_provider()
    vector = await provider.embed(query)

    _QUERY_EMBEDDING_CACHE[key] = tuple(vector)
    _QUERY_EMBEDDING_CACHE.move_to_end(key)
    while len(_QUERY_EMBEDDING_CACHE) > _QUERY_EMBEDDING_CACHE_MAX:
        _QUERY_EMBEDDING_CACHE.popitem(last=False)

    return list(vector)


def _assert_query_dim(query_vector: list[float], corpus_dim: int | None = None) -> None:
    """Bloqueia só quando há dim versionada no corpus incompatível."""
    if corpus_dim is not None and len(query_vector) != corpus_dim:
        raise EmbeddingDimensionError(
            f"Dimensão da query ({len(query_vector)}) incompatível com "
            f"corpus embedding_dim ({corpus_dim})."
        )
    if len(query_vector) != settings.embeddings_dim:
        logger.warning(
            "Dimensão da query (%d) difere de embeddings_dim (%d).",
            len(query_vector),
            settings.embeddings_dim,
        )


async def _tem_embeddings(db) -> bool:
    """Indica se há chunks com embedding armazenado (busca semântica viável)."""
    try:
        result = await db.execute(
            select(func.count()).select_from(LegalChunk).where(
                LegalChunk.embedding.isnot(None),
                LegalChunk.embedding != "",
            )
        )
        if result.scalar_one() > 0:
            return True
        # pgvector column (Postgres)
        bind = db.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            row = (
                await db.execute(
                    text(
                        "SELECT COUNT(*) FROM legal_chunks "
                        "WHERE embedding_vector IS NOT NULL"
                    )
                )
            ).scalar()
            return bool(row and int(row) > 0)
        return False
    except Exception:
        logger.exception("Falha ao verificar embeddings no corpus")
        return False


async def _search_semantic_pgvector(
    db,
    query_vector: list[float],
    top_k: int,
    law_numbers: list[str] | None,
) -> list[dict] | None:
    """Busca via pgvector; None se coluna ausente / dialeto não Postgres."""
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return None

    try:
        # Verifica se há vetores
        count = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM legal_chunks "
                    "WHERE embedding_vector IS NOT NULL"
                )
            )
        ).scalar()
        if not count:
            return None

        # Bloqueia se chunks versionados tiverem dim incompatível
        dim_row = (
            await db.execute(
                text(
                    "SELECT embedding_dim FROM legal_chunks "
                    "WHERE embedding_vector IS NOT NULL "
                    "AND embedding_dim IS NOT NULL LIMIT 1"
                )
            )
        ).fetchone()
        if dim_row and dim_row[0] and int(dim_row[0]) != len(query_vector):
            raise EmbeddingDimensionError(
                f"Dimensão do corpus ({dim_row[0]}) incompatível com "
                f"query ({len(query_vector)})."
            )

        vec_literal = "[" + ",".join(str(float(x)) for x in query_vector) + "]"
        params: dict = {"qvec": vec_literal, "top_k": top_k}
        law_filter = ""
        if law_numbers:
            law_filter = "AND ld.law_number = ANY(:laws)"
            params["laws"] = list(law_numbers)

        sql = text(
            f"""
            SELECT lc.id, ld.law_number, ld.law_title, lc.article, lc.section,
                   lc.chunk_text,
                   1 - (lc.embedding_vector <=> CAST(:qvec AS vector)) AS score
            FROM legal_chunks lc
            JOIN legal_documents ld ON ld.id = lc.legal_document_id
            WHERE lc.embedding_vector IS NOT NULL
            {law_filter}
            ORDER BY lc.embedding_vector <=> CAST(:qvec AS vector)
            LIMIT :top_k
            """
        )
        rows = (await db.execute(sql, params)).mappings().all()
        scored = [
            {
                "id": str(r["id"]),
                "law_number": r["law_number"],
                "law_title": r["law_title"],
                "article": r["article"],
                "section": r["section"],
                "chunk_text": r["chunk_text"],
                "score": float(r["score"] or 0.0),
            }
            for r in rows
        ]
        logger.info("Busca semântica pgvector: top %d", len(scored))
        return scored
    except EmbeddingDimensionError:
        raise
    except Exception:
        logger.warning("pgvector indisponível; fallback Python", exc_info=True)
        return None


async def _search_semantic(
    db,
    query: str,
    top_k: int,
    law_numbers: list[str] | None,
) -> list[dict]:
    """Busca por similaridade de cosseno sobre os embeddings armazenados."""
    try:
        import app.services.rag.retriever as retriever_module

        provider = retriever_module.get_embeddings_provider()
        query_vector = await _query_embedding_cached(query, provider.provider_name)
    except Exception:
        logger.warning(
            "Embeddings indisponíveis para a consulta; usando fallback textual"
        )
        return []

    try:
        _assert_query_dim(query_vector)
    except EmbeddingDimensionError:
        logger.error("Query embedding com dimensão incompatível — busca bloqueada")
        raise

    pg_hits = await _search_semantic_pgvector(db, query_vector, top_k, law_numbers)
    if pg_hits is not None:
        return pg_hits

    # Dim versionada no corpus (se houver)
    sample_dim = (
        await db.execute(
            select(LegalChunk.embedding_dim).where(
                LegalChunk.embedding_dim.isnot(None),
                LegalChunk.embedding.isnot(None),
            ).limit(1)
        )
    ).scalar_one_or_none()
    if sample_dim is not None:
        _assert_query_dim(query_vector, int(sample_dim))

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
        if chunk.embedding_dim and chunk.embedding_dim != len(query_vector):
            continue
        try:
            vector = json.loads(chunk.embedding)
        except (TypeError, ValueError):
            continue
        if not vector or len(vector) != len(query_vector):
            continue
        scored.append({
            "id": str(chunk.id),
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

    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
