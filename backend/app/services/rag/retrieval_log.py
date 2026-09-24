"""Persistência de retrieval_run a partir de um retrieve()."""

from __future__ import annotations

import hashlib
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.retrieval import RetrievalRun
from app.services.rag.corpus_version import compute_corpus_version
from app.utils.request_context import request_id_var

logger = logging.getLogger(__name__)


def _query_hash(query: str) -> str:
    return hashlib.sha256((query or "").encode("utf-8")).hexdigest()


async def record_retrieval_run(
    db: AsyncSession,
    *,
    operation_type: str,
    query: str,
    chunks: list,
    params: dict | None = None,
    filters: dict | None = None,
    classification: str | None = None,
) -> RetrievalRun | None:
    """Grava a recuperação. Falha aberta: não derruba análise/chat."""
    try:
        version, _ = await compute_corpus_version(db)
        rid = request_id_var.get()
        run = RetrievalRun(
            request_id=None if rid in (None, "-") else rid,
            operation_type=operation_type,
            query_hash=_query_hash(query),
            corpus_version=version,
            embedding_model=settings.embeddings_model,
            rerank_model=settings.rag_rerank_mode,
            params=params or {},
            retrieved_ids=[str(getattr(c, "id", "") or "") for c in chunks],
            scores=[
                {
                    "id": str(getattr(c, "id", "") or ""),
                    "score": float(getattr(c, "score", 0.0) or 0.0),
                }
                for c in chunks
            ],
            filters=filters or {},
            classification=classification,
        )
        db.add(run)
        await db.flush()
        return run
    except Exception:
        logger.exception("Falha ao persistir retrieval_run")
        return None
