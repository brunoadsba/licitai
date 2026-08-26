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

_legal_context_cache: dict[str, tuple[float, list["RetrievedChunk"]]] = {}


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

    cache_key = hashlib.sha256(f"{cleaned}|{top_k}|{law_numbers}|{use_semantic}".encode()).hexdigest()
    cached = _legal_context_cache.get(cache_key)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        logger.debug("rag_cache_hit query_hash=%s", cache_key[:12])
        return cached[1]

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
            result = _para_chunks(rows)
            _legal_context_cache[cache_key] = (time.time(), result)
            return result

    result = _para_chunks(
        await _search_textual(db, cleaned, top_k, law_numbers)
    )
    _legal_context_cache[cache_key] = (time.time(), result)
    return result


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


def _clean_query(query: str) -> str:
    """Normaliza a consulta para busca (minúsculas, remove ruído)."""
    cleaned = query.strip().lower()[:MAX_QUERY_CHARS]
    return " ".join(cleaned.split())
