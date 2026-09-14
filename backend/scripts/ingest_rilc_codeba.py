"""
Ingestão do RILC CODEBA completo no RAG.

Fonte canônica: backend/data/rilc/source/provenance.json + PDF local.
Se o PDF não existir, baixa a URL canônica (fallback: espelho) e valida SHA-256.

Uso (na pasta backend/):
    PYTHONPATH=. python scripts/ingest_rilc_codeba.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import sys
import urllib.request
from pathlib import Path

import pdfplumber
from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, async_session_factory, engine
from app.models.legal import LegalChunk, LegalDocument
from app.services.rag.loader import build_fts_index, ingest_law_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ingest_rilc_codeba")

SOURCE_DIR = Path(__file__).resolve().parent.parent / "data" / "rilc" / "source"
PROVENANCE_PATH = SOURCE_DIR / "provenance.json"
LEGACY_STUB_LAW_NUMBERS = ("RILC-CODEBA-2023",)

_HEADER_RE = re.compile(
    r"^REGULAMENTO\s+LICITAÇÕES\s+E\s+CONTRATOS\s+Rev\.\s*\d+\s+Pág\.\s*\d+\s+de\s*\d+",
    re.IGNORECASE,
)


def _load_provenance() -> dict:
    if not PROVENANCE_PATH.exists():
        raise FileNotFoundError(f"Manifesto ausente: {PROVENANCE_PATH}")
    return json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    logger.info("Baixando %s → %s", url, dest.name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "LicitAI-RILC-ingest/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as out:
        out.write(resp.read())


def ensure_pdf(meta: dict) -> Path:
    """Garante PDF local com hash pinado; baixa canônica/espelho se necessário."""
    pdf_path = SOURCE_DIR / meta["arquivo_local"]
    expected = meta["sha256"].lower()

    if pdf_path.exists():
        digest = _sha256(pdf_path)
        if digest == expected:
            logger.info("PDF local OK (%s bytes, sha256 confere)", pdf_path.stat().st_size)
            return pdf_path
        logger.warning(
            "Hash local diverge (got %s, expected %s) — rebaixando",
            digest[:16],
            expected[:16],
        )

    for label, url in (
        ("canônica", meta["url_canonica"]),
        ("espelho", meta["url_espelho"]),
    ):
        try:
            _download(url, pdf_path)
            digest = _sha256(pdf_path)
            if digest == expected:
                logger.info("Download %s OK (sha256 confere)", label)
                return pdf_path
            logger.error("Download %s com hash inválido: %s", label, digest)
        except Exception as exc:  # noqa: BLE001 — tenta próximo espelho
            logger.error("Falha no download %s (%s): %s", label, url, exc)

    raise RuntimeError(
        "Não foi possível obter o PDF do RILC com o SHA-256 pinado em provenance.json"
    )


def extract_text_with_pages(pdf_path: Path) -> tuple[str, int, list[int]]:
    """Extrai texto com marcadores `# Página N`. Retorna (texto, páginas, páginas_vazias)."""
    parts: list[str] = []
    empty_pages: list[int] = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            raw = page.extract_text() or ""
            lines = []
            for line in raw.splitlines():
                s = line.strip()
                if not s or _HEADER_RE.match(s):
                    continue
                lines.append(s)
            if not lines:
                empty_pages.append(i)
                continue
            parts.append(f"# Página {i}")
            parts.extend(lines)
    text = "\n".join(parts)
    return text, total, empty_pages


async def _drop_legacy_stubs(db) -> None:
    for law_number in LEGACY_STUB_LAW_NUMBERS:
        existing = await db.execute(
            select(LegalDocument).where(LegalDocument.law_number == law_number)
        )
        old = existing.scalar_one_or_none()
        if not old:
            continue
        await db.execute(
            delete(LegalChunk).where(LegalChunk.legal_document_id == old.id)
        )
        await db.delete(old)
        logger.info("Removido stub legado %s", law_number)


async def run_ingest() -> None:
    meta = _load_provenance()
    pdf_path = ensure_pdf(meta)
    text, pages, empty = extract_text_with_pages(pdf_path)
    logger.info(
        "Extração: %d páginas, %d chars, %d páginas sem texto",
        pages,
        len(text),
        len(empty),
    )
    if empty:
        logger.warning("Páginas sem texto extraído: %s", empty[:20])

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        await _drop_legacy_stubs(db)
        doc = await ingest_law_text(
            db,
            content=text,
            law_number=meta["law_number"],
            law_title=meta["titulo"],
            source_url=meta["url_canonica"],
            version=meta["version"],
        )
        await build_fts_index(db)
        await db.commit()
        logger.info(
            "RILC ingerido: %s — %d chunks (versão %s)",
            doc.law_number,
            doc.total_chunks,
            meta["version"],
        )


if __name__ == "__main__":
    asyncio.run(run_ingest())
