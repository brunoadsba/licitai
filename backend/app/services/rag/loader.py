"""
Loader do corpus jurídico (RAG).

Faz a ingestão do texto integral das leis no banco:
1. Parseia o texto da lei em chunks (um por artigo)
2. Salva LegalDocument + LegalChunk
3. Popula índice FTS5 (SQLite) para busca por texto
"""

import logging
import re
from dataclasses import dataclass

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal import LegalChunk, LegalDocument

logger = logging.getLogger(__name__)

# Marcos estruturais da lei
_SECTION_RE = re.compile(r"^(TÍTULO|CAPÍTULO|SEÇÃO|SUBSECÇÃO)\s+[IVXLCDM0-9]+")
_ARTICLE_RE = re.compile(r"^Art\.\s*\d+[º\-A-Z]?")
_FOOTER_MARK = "Este texto não substitui o publicado no DOU"


@dataclass
class LawChunk:
    """Chunk de lei: um artigo com seus parágrafos e incisos."""

    article: str
    section: str
    text: str


def parse_law_text(content: str) -> list[LawChunk]:
    """
    Divide o texto integral de uma lei em chunks por artigo.

    Agrupa o artigo com seus §§ e incisos. Rastreia título/capítulo.
    Ignora cabeçalho (antes do 1º artigo) e rodapé (após a nota DOU).
    """
    chunks: list[LawChunk] = []
    current_article: str | None = None
    current_section = ""
    buffer: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _FOOTER_MARK in line:
            break

        # Novo artigo: fecha o chunk anterior e inicia outro
        if _ARTICLE_RE.match(line):
            if current_article and buffer:
                chunks.append(
                    LawChunk(
                        article=current_article,
                        section=current_section,
                        text="\n".join(buffer),
                    )
                )
            current_article = _extract_article_ref(line)
            buffer = [line]
            continue

        # Novo título/capítulo/seção (linha seguinte é o nome)
        if _SECTION_RE.match(line):
            current_section = line
            continue
        if current_section and not current_article and re.match(r"^[A-ZÀ-Ú\s]+$", line):
            current_section = f"{current_section} - {line}"
            continue

        # Conteúdo do artigo atual (parágrafos, incisos, texto)
        if current_article:
            buffer.append(line)
        # Sem artigo ainda = cabeçalho da lei, ignora

    # Fecha o último chunk
    if current_article and buffer:
        chunks.append(
            LawChunk(
                article=current_article,
                section=current_section,
                text="\n".join(buffer),
            )
        )

    return chunks


def _extract_article_ref(line: str) -> str:
    """Extrai a referência do artigo ('Art. 6º', 'Art. 19-A.')."""
    match = re.match(r"^Art\.\s*([^\s]+)", line)
    return f"Art. {match.group(1).rstrip('.')}" if match else line[:60]


def parse_extra_text(content: str, chunk_chars: int = 1500) -> list[LawChunk]:
    """
    Divide um documento jurídico genérico (acórdão TCU, instrução RILC,
    ementa) em chunks por parágrafo agrupado até `chunk_chars`.

    Linhas de cabeçalho iniciadas com '#' são ignoradas (metadata).
    """
    paragrafos: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if _FOOTER_MARK in line:
            break
        paragrafos.append(line)

    chunks: list[LawChunk] = []
    buffer: list[str] = []
    tamanho = 0
    for par in paragrafos:
        if buffer and tamanho + len(par) > chunk_chars:
            chunks.append(LawChunk(
                article=f"Trecho {len(chunks) + 1}",
                section="",
                text="\n".join(buffer),
            ))
            buffer = []
            tamanho = 0
        buffer.append(par)
        tamanho += len(par) + 1
    if buffer:
        chunks.append(LawChunk(
            article=f"Trecho {len(chunks) + 1}",
            section="",
            text="\n".join(buffer),
        ))
    return chunks


async def _persist_document(
    db: AsyncSession,
    chunks: list[LawChunk],
    law_number: str,
    law_title: str,
    source_url: str | None = None,
    version: str | None = None,
) -> LegalDocument:
    """Persiste um documento legal (idempotente: substitui versão anterior)."""
    existing = await db.execute(
        select(LegalDocument).where(LegalDocument.law_number == law_number)
    )
    old_doc = existing.scalar_one_or_none()
    if old_doc:
        await db.execute(
            delete(LegalChunk).where(
                LegalChunk.legal_document_id == old_doc.id
            )
        )
        await db.delete(old_doc)
        await db.flush()

    doc = LegalDocument(
        law_number=law_number,
        law_title=law_title,
        source_url=source_url,
        version=version,
        total_chunks=len(chunks),
    )
    db.add(doc)
    await db.flush()

    for idx, chunk in enumerate(chunks):
        db.add(
            LegalChunk(
                legal_document_id=doc.id,
                chunk_index=idx,
                article=chunk.article,
                section=chunk.section,
                chunk_text=chunk.text,
                doc_metadata={
                    "law_number": law_number,
                    "law_title": law_title,
                    "article": chunk.article,
                },
            )
        )

    await db.flush()
    logger.info(
        "Documento %s ingerido: %d chunks", law_number, len(chunks)
    )
    return doc


async def ingest_law_text(
    db: AsyncSession,
    content: str,
    law_number: str,
    law_title: str,
    source_url: str | None = None,
    version: str | None = None,
) -> LegalDocument:
    """Ingere o texto de uma lei no banco, substituindo versão anterior."""
    chunks = parse_law_text(content)
    if not chunks:
        raise ValueError(f"Nenhum artigo encontrado em {law_number}")
    return await _persist_document(
        db, chunks, law_number, law_title, source_url, version
    )


async def ingest_extra_document(
    db: AsyncSession,
    content: str,
    law_number: str,
    law_title: str,
    source_url: str | None = None,
    version: str | None = None,
) -> LegalDocument:
    """Ingere um documento jurídico genérico (acórdão/instrução/ementa)."""
    chunks = parse_extra_text(content)
    if not chunks:
        raise ValueError(f"Nenhum conteúdo encontrado em {law_number}")
    return await _persist_document(
        db, chunks, law_number, law_title, source_url, version
    )


async def build_fts_index(db: AsyncSession) -> None:
    """Recria o índice FTS5 (apenas SQLite) para busca por texto."""
    if db.bind and db.bind.dialect.name != "sqlite":
        return

    # Garante que chunks pendentes estejam visíveis (raw SQL não faz autoflush)
    await db.flush()

    await db.execute(text("DROP TABLE IF EXISTS legal_chunks_fts"))
    await db.execute(
        text(
            "CREATE VIRTUAL TABLE legal_chunks_fts USING fts5("
            "chunk_id UNINDEXED, article UNINDEXED, "
            "section UNINDEXED, chunk_text)"
        )
    )

    result = await db.execute(
        text(
            "SELECT id, article, section, chunk_text FROM legal_chunks "
            "ORDER BY chunk_index"
        )
    )
    rows = result.fetchall()
    for row in rows:
        await db.execute(
            text(
                "INSERT INTO legal_chunks_fts "
                "(chunk_id, article, section, chunk_text) "
                "VALUES (:chunk_id, :article, :section, :chunk_text)"
            ),
            {
                "chunk_id": str(row[0]),
                "article": row[1] or "",
                "section": row[2] or "",
                "chunk_text": row[3],
            },
        )

    logger.info("Índice FTS5 reconstruído: %d chunks", len(rows))
