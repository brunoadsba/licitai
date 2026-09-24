"""
Retriever do corpus jurídico (RAG).

Busca os artigos mais relevantes para uma consulta combinando busca
textual (FTS5/FTS Postgres) com busca semântica (cosseno) via Reciprocal Rank
Fusion, com fallback textual automático quando a semântica falha.

Retorna chunks com a lei, o artigo e o texto integral para o LLM.
"""

import hashlib
import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embeddings.base import (
    get_embeddings_provider,  # noqa: F401 (re-export: contrato de monkeypatch em testes)
)
from app.services.rag.backends import (  # noqa: F401
    _search_postgres,
    _search_sqlite,
    _search_textual,
)
from app.services.rag.legal_cache import (  # noqa: F401
    _cache_stats,
    _clear_legal_context_cache,
    cache_get,
    cache_put,
)
from app.services.rag.rrf import rrf_merge
from app.services.rag.quarantine import filter_active_rows
from app.services.rag.semantic import (
    _clear_query_embedding_cache,  # noqa: F401 (re-export: contrato de testes)
    _cosseno,  # noqa: F401 (re-export: contrato de testes)
    _search_semantic,
    _tem_embeddings,
)

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
MAX_QUERY_CHARS = 500


@dataclass
class RetrievedChunk:
    """Chunk recuperado do corpus jurídico."""

    id: str
    law_number: str
    law_title: str
    article: str
    section: str
    text: str
    score: float


async def retrieve(
    db: AsyncSession,
    query: str,
    top_k: int | None = None,
    law_numbers: list[str] | None = None,
    use_semantic: bool | None = None,
    llm=None,
    allow_semantic: bool | None = None,
    allow_llm_rerank: bool | None = None,
    classification: str | None = None,
) -> list[RetrievedChunk]:
    """Recupera artigos por RRF. `allow_semantic=False` não gera embedding da query."""
    from app.config import settings
    from app.services.privacy import normalize_classification
    from app.services.rag.corpus_version import compute_corpus_version
    from app.services.rag.rerank import heuristic_rerank, llm_rerank
    from app.utils.metrics import metrics

    cleaned = _clean_query(query)
    if not cleaned:
        return []

    eff_top_k = top_k or getattr(settings, "rag_top_k", 0) or DEFAULT_TOP_K
    rerank_mode = getattr(settings, "rag_rerank_mode", "heuristic")
    candidates = getattr(settings, "rag_candidates", 20) or 0
    fetch_k = max(eff_top_k, candidates) if rerank_mode != "off" and candidates else eff_top_k
    rerank_llm = None if allow_llm_rerank is False else llm
    semantic_on = False if allow_semantic is False else use_semantic
    classif = normalize_classification(classification) or "unclassified"
    corpus_version, _ = await compute_corpus_version(db)

    cache_key = hashlib.sha256(
        (
            f"{cleaned}|{eff_top_k}|{law_numbers}|{use_semantic}|"
            f"{allow_semantic}|{allow_llm_rerank}|{rerank_mode}|{fetch_k}|"
            f"{rerank_llm is not None}|{corpus_version}|{classif}"
        ).encode()
    ).hexdigest()
    cached = cache_get(cache_key)
    if cached is not None:
        metrics.inc("rag_cache_hit")
        logger.info("rag.cache hit=1 key=%s classif=%s", cache_key[:12], classif)
        from app.services.rag.quarantine import quarantine_only_hit

        quarantine_only_hit.set(cached[1])
        return cached[0]
    metrics.inc("rag_cache_miss")
    logger.info("rag.cache hit=0 key=%s classif=%s", cache_key[:12], classif)

    if semantic_on is None:
        semantic_on = await _tem_embeddings(db)

    if semantic_on:
        try:
            sem_rows = await _search_semantic(
                db,
                cleaned,
                fetch_k,
                law_numbers,
                classification=classif,
                corpus_version=corpus_version,
            )
        except Exception:
            logger.exception("Falha na busca semântica; usando fallback textual")
            sem_rows = []

        try:
            text_rows = await _search_textual(db, cleaned, fetch_k, law_numbers)
        except Exception:
            logger.exception("Falha na busca textual; seguindo apenas com semântica")
            text_rows = []

        rows = rrf_merge(sem_rows, text_rows, fetch_k)
        if rows:
            if rerank_mode in ("heuristic", "llm"):
                rows = heuristic_rerank(cleaned, rows)
            if rerank_mode == "llm" and rerank_llm is not None:
                rows = await llm_rerank(rerank_llm, cleaned, rows, top_k)
            rows, dropped = filter_active_rows(rows)
            return await _cache_result(
                db, cleaned, law_numbers, cache_key, rows[:eff_top_k], dropped
            )

    textual = await _search_textual(db, cleaned, eff_top_k, law_numbers)
    textual, dropped = filter_active_rows(textual)
    return await _cache_result(
        db, cleaned, law_numbers, cache_key, textual, dropped
    )


async def _cache_result(
    db,
    cleaned: str,
    law_numbers: list[str] | None,
    cache_key: str,
    rows: list[dict],
    dropped: int,
) -> list[RetrievedChunk]:
    if dropped:
        logger.info("rag.quarantine_excluded dropped=%d kept=%d", dropped, len(rows))
    result = _para_chunks(rows)
    if result:
        from app.services.rag.hierarchy import expand_hierarchical

        result = await expand_hierarchical(db, result)
    if not result:
        peek = await _search_textual(
            db, cleaned, 5, law_numbers, exclude_quarantine=False
        )
        _, dropped = filter_active_rows(peek)
    only = not result and dropped > 0
    cache_put(cache_key, result, only)
    return result


def _para_chunks(rows: list[dict]) -> list[RetrievedChunk]:
    """Converte linhas de busca em objetos RetrievedChunk."""
    return [
        RetrievedChunk(
            id=str(row.get("id") or row.get("chunk_id") or ""),
            law_number=row["law_number"],
            law_title=row["law_title"],
            article=row["article"] or "",
            section=row["section"] or "",
            text=row["chunk_text"],
            score=float(row["score"]),
        )
        for row in rows
    ]


def _clean_query(query: str) -> str:
    """Normaliza a consulta para busca (minúsculas, remove ruído)."""
    cleaned = query.strip().lower()[:MAX_QUERY_CHARS]
    return " ".join(cleaned.split())
