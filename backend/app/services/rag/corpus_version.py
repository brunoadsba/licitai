"""Versão imutável do corpus jurídico (hash do manifesto)."""

from __future__ import annotations

import hashlib
import json
import time

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal import LegalDocument

_CACHE_TTL_SECONDS = 300
_cache: tuple[float, str, list[dict]] | None = None


def _canonical(rows: list[dict]) -> str:
    return json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def hash_manifest(rows: list[dict]) -> str:
    """SHA-256 estável do manifesto ordenado por law_number."""
    return hashlib.sha256(_canonical(rows).encode("utf-8")).hexdigest()


async def compute_corpus_version(
    db: AsyncSession,
) -> tuple[str, list[dict]]:
    """Retorna (hash, manifesto) dos legal_documents ativos."""
    global _cache
    now = time.time()
    if _cache and now - _cache[0] < _CACHE_TTL_SECONDS:
        return _cache[1], _cache[2]

    result = await db.execute(
        select(
            LegalDocument.law_number,
            LegalDocument.version,
            LegalDocument.total_chunks,
        )
        .where(
            or_(
                LegalDocument.ingest_status == "published",
                LegalDocument.ingest_status.is_(None),
            )
        )
        .order_by(LegalDocument.law_number)
    )
    rows = [
        {
            "law_number": law_number,
            "version": version,
            "total_chunks": total_chunks,
        }
        for law_number, version, total_chunks in result.all()
    ]
    digest = hash_manifest(rows)
    _cache = (now, digest, rows)
    return digest, rows


def clear_corpus_version_cache() -> None:
    """Limpa o cache (testes)."""
    global _cache
    _cache = None
