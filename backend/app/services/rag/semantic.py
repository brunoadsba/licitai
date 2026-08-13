"""
Busca semântica sobre embeddings do corpus jurídico.

Consulta embeddings pré-computados (coluna `legal_chunks.embedding`) com
cache LRU de vetores de consulta e similaridade de cosseno.
"""

import asyncio
import json
import logging
from collections import OrderedDict

from sqlalchemy import func, select

from app.config import settings
from app.models.legal import LegalChunk, LegalDocument
from app.services.embeddings.base import get_embeddings_provider

logger = logging.getLogger(__name__)

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

    # Resolve via módulo retriever em runtime: testes patcheiam
    # "app.services.rag.retriever.get_embeddings_provider" via monkeypatch.
    import app.services.rag.retriever as retriever_module

    provider = retriever_module.get_embeddings_provider()
    vector = await provider.embed(query)

    async with _QUERY_EMBEDDING_LOCK:
        _QUERY_EMBEDDING_CACHE[key] = tuple(vector)
        _QUERY_EMBEDDING_CACHE.move_to_end(key)
        while len(_QUERY_EMBEDDING_CACHE) > _QUERY_EMBEDDING_CACHE_MAX:
            _QUERY_EMBEDDING_CACHE.popitem(last=False)

    return list(vector)


async def _tem_embeddings(db) -> bool:
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
    db,
    query: str,
    top_k: int,
    law_numbers: list[str] | None,
) -> list[dict]:
    """Busca por similaridade de cosseno sobre os embeddings armazenados."""
    try:
        # Resolve via módulo retriever em runtime: testes patcheiam
        # "app.services.rag.retriever.get_embeddings_provider" via monkeypatch.
        import app.services.rag.retriever as retriever_module

        provider = retriever_module.get_embeddings_provider()
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
