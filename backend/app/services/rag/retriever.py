"""
Retriever do corpus jurídico (RAG).

Busca os artigos mais relevantes para uma consulta combinando busca
textual (FTS5/ILIKE) com busca semântica (cosseno) via Reciprocal Rank
Fusion, com fallback textual automático quando a semântica falha.

Retorna chunks com a lei, o artigo e o texto integral para o LLM.
"""

import hashlib
import logging
import time
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
_CACHE_TTL_SECONDS = 3600

_legal_context_cache: dict[str, tuple[float, list["RetrievedChunk"], bool]] = {}


def _clear_legal_context_cache() -> None:
    """Limpa o cache de contexto jurídico (usado em testes)."""
    _legal_context_cache.clear()


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
) -> list[RetrievedChunk]:
    """Recupera artigos por RRF. `allow_semantic=False` não gera embedding da query."""
    from app.config import settings
    from app.services.rag.rerank import heuristic_rerank, llm_rerank

    cleaned = _clean_query(query)
    if not cleaned:
        return []

    eff_top_k = top_k or getattr(settings, "rag_top_k", 0) or DEFAULT_TOP_K
    rerank_mode = getattr(settings, "rag_rerank_mode", "heuristic")
    candidates = getattr(settings, "rag_candidates", 20) or 0
    fetch_k = max(eff_top_k, candidates) if rerank_mode != "off" and candidates else eff_top_k
    rerank_llm = None if allow_llm_rerank is False else llm
    semantic_on = False if allow_semantic is False else use_semantic

    cache_key = hashlib.sha256(
        (
            f"{cleaned}|{eff_top_k}|{law_numbers}|{use_semantic}|"
            f"{allow_semantic}|{allow_llm_rerank}|{rerank_mode}|{fetch_k}|"
            f"{rerank_llm is not None}"
        ).encode()
    ).hexdigest()
    cached = _legal_context_cache.get(cache_key)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        logger.debug("rag_cache_hit query_hash=%s", cache_key[:12])
        from app.services.rag.quarantine import quarantine_only_hit

        quarantine_only_hit.set(cached[2])
        return cached[1]

    if semantic_on is None:
        semantic_on = await _tem_embeddings(db)

    if semantic_on:
        try:
            sem_rows = await _search_semantic(db, cleaned, fetch_k, law_numbers)
        except Exception:
            logger.exception("Falha na busca semântica; usando fallback textual")
            sem_rows = []

        try:
            text_rows = await _search_textual(db, cleaned, fetch_k, law_numbers)
        except Exception:
            logger.exception("Falha na busca textual; seguindo apenas com semântica")
            text_rows = []

        rows = _rrf(sem_rows, text_rows, fetch_k)
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
    if not result:
        peek = await _search_textual(
            db, cleaned, 5, law_numbers, exclude_quarantine=False
        )
        _, dropped = filter_active_rows(peek)
    only = not result and dropped > 0
    _legal_context_cache[cache_key] = (time.time(), result, only)
    return result


def _rrf(
    sem_rows: list[dict],
    text_rows: list[dict],
    top_k: int,
    k: int = 60,
) -> list[dict]:
    """Combina rankings via Reciprocal Rank Fusion clássico (pesos iguais).

    Pesos iguais por backend: evidência de um lado só (ex.: textual rank 0)
    supera ruído duplo de chunks irrelevantes — com 600 chunks, peso
    assimétrico enterrava o acerto fora dos candidatos.
    """

    def _key(row: dict) -> tuple:
        return (
            row.get("law_number"),
            row.get("article") or "",
            row.get("chunk_text") or "",
        )

    scores: dict[tuple, float] = {}
    merged: dict[tuple, dict] = {}

    for rank, row in enumerate(sem_rows):
        key = _key(row)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        merged.setdefault(key, row)
    for rank, row in enumerate(text_rows):
        key = _key(row)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        merged.setdefault(key, row)

    ordered = sorted(
        merged.items(),
        key=lambda kv: scores[kv[0]],
        reverse=True,
    )
    return [row for _, row in ordered[:top_k]]


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
