"""Semeia um corpus mínimo (CI) a partir de seed_corpus.json."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal import LegalChunk, LegalDocument
from app.services.rag.loader import build_fts_index

SEED_PATH = Path(__file__).resolve().parent / "seed_corpus.json"


async def seed_eval_corpus(db: AsyncSession, path: Path | None = None) -> int:
    data = json.loads((path or SEED_PATH).read_text(encoding="utf-8"))
    total = 0
    for doc in data["documents"]:
        legal = LegalDocument(
            law_number=doc["law_number"],
            law_title=doc["law_title"],
            version=doc.get("version"),
            total_chunks=len(doc["chunks"]),
        )
        db.add(legal)
        await db.flush()
        for idx, chunk in enumerate(doc["chunks"]):
            db.add(
                LegalChunk(
                    legal_document_id=legal.id,
                    chunk_index=idx,
                    article=chunk["article"],
                    section="",
                    chunk_text=chunk["text"],
                )
            )
            total += 1
    await build_fts_index(db)
    await db.commit()
    return total
