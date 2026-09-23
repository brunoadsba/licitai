"""Handlers por tipo de job — extraído de `app/worker.py`."""

import logging
import uuid

from sqlalchemy import select

from app.database import async_session_factory
from app.models.document import Document
from app.services.analyzer.engine import run_analysis
from app.services.comparator.runner import executar_comparacao
from app.services.privacy import PrivacyPolicyError
from app.services.upload_service import parse_e_inserir_itens

logger = logging.getLogger(__name__)


async def _run_analysis_job(payload: dict) -> None:
    analysis_id = uuid.UUID(payload["analysis_id"])
    document_id = uuid.UUID(payload["document_id"])
    async with async_session_factory() as db:
        try:
            await run_analysis(db, analysis_id, document_id)
        except PrivacyPolicyError:
            await db.commit()
            raise
        await db.commit()


async def _run_comparacao_job(payload: dict) -> None:
    comparacao_id = uuid.UUID(payload["comparacao_id"])
    tr_document_id = uuid.UUID(payload["tr_document_id"])
    molde_id = uuid.UUID(payload["molde_id"])
    propostas_ids = [uuid.UUID(x) for x in payload.get("propostas_ids") or []]
    await executar_comparacao(
        comparacao_id, tr_document_id, molde_id, propostas_ids
    )


async def _run_parse_job(payload: dict) -> None:
    document_id = uuid.UUID(payload["document_id"])
    async with async_session_factory() as db:
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            raise RuntimeError(f"Documento {document_id} não encontrado para parse.")
        document.status = "parsing"
        await db.flush()
        ok = await parse_e_inserir_itens(db, document, document.file_type)
        if not ok:
            raise RuntimeError(document.error_message or "Falha no parse.")
        await db.commit()
