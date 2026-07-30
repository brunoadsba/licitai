"""
Endpoints para análise de documentos e geração de relatórios.
"""

import logging
import uuid
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db, async_session_factory
from app.models.document import Document
from app.models.analysis import Analysis, Correction
from app.schemas.analysis import (
    AnalysisStartResponse,
    AnalysisDetailResponse,
    CorrectionResponse,
    ReportResponse,
    ScoreDetail,
)
from app.services.analyzer.engine import run_analysis


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Análise"])


@router.post(
    "/{document_id}/start",
    response_model=AnalysisStartResponse,
    status_code=202,
    summary="Iniciar análise",
    description="Inicia a análise completa de um documento usando IA.",
)
async def start_analysis(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Inicia análise em background."""

    # Verificar se documento existe e está parseado
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    if document.status not in ("parsed", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Documento não está pronto para análise. Status atual: {document.status}",
        )

    # Verificar se já existe análise em andamento
    running = await db.execute(
        select(Analysis).where(
            Analysis.document_id == document_id,
            Analysis.status.in_(["pending", "running"]),
        )
    )
    if running.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Já existe uma análise em andamento para este documento.",
        )

    # Criar registro de análise
    analysis = Analysis(
        document_id=document_id,
        status="pending",
        llm_provider=settings.llm_provider,
        llm_model=_get_current_model(),
        total_items=document.total_items,
    )
    db.add(analysis)
    await db.flush()

    analysis_id = analysis.id

    # Executar análise em background
    background_tasks.add_task(_run_analysis_background, analysis_id, document_id)

    return AnalysisStartResponse(
        analysis_id=analysis_id,
        message="Análise iniciada. Acompanhe o progresso pelo endpoint de status.",
    )


async def _run_analysis_background(
    analysis_id: uuid.UUID, document_id: uuid.UUID
) -> None:
    """Executa a análise em background com sessão própria do banco."""
    async with async_session_factory() as db:
        try:
            await run_analysis(db, analysis_id, document_id)
            await db.commit()
        except Exception:
            logger.exception("Erro na análise %s", analysis_id)
            await db.rollback()

            # Marcar análise como erro
            try:
                result = await db.execute(
                    select(Analysis).where(Analysis.id == analysis_id)
                )
                analysis = result.scalar_one_or_none()
                if analysis:
                    analysis.status = "error"
                    analysis.error_message = "Erro interno durante a análise."
                    await db.commit()
            except Exception:
                logger.exception("Erro ao atualizar status da análise %s", analysis_id)


@router.get(
    "/{analysis_id}",
    response_model=AnalysisDetailResponse,
    summary="Status da análise",
    description="Retorna o status e resultados parciais/completos de uma análise.",
)
async def get_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retorna detalhes da análise com correções."""
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.corrections))
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    return AnalysisDetailResponse.model_validate(analysis)


@router.get(
    "/{analysis_id}/report",
    response_model=ReportResponse,
    summary="Relatório da análise",
    description="Retorna o relatório completo de uma análise finalizada.",
)
async def get_report(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Gera relatório consolidado."""
    result = await db.execute(
        select(Analysis)
        .options(
            selectinload(Analysis.corrections),
            selectinload(Analysis.document),
        )
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    corrections = [CorrectionResponse.model_validate(c) for c in analysis.corrections]

    # Contagem por categoria e severidade
    category_counts = dict(Counter(c.category for c in corrections))
    severity_counts = dict(Counter(c.severity for c in corrections))

    scores = [
        ScoreDetail(label="Nota Geral", score=float(analysis.score_overall) if analysis.score_overall else None),
        ScoreDetail(label="Segurança Jurídica", score=float(analysis.score_juridical) if analysis.score_juridical else None),
        ScoreDetail(label="Qualidade Técnica", score=float(analysis.score_technical) if analysis.score_technical else None),
        ScoreDetail(label="Qualidade da Redação", score=float(analysis.score_writing) if analysis.score_writing else None),
        ScoreDetail(label="Conformidade Estrutural", score=float(analysis.score_structural) if analysis.score_structural else None),
    ]

    return ReportResponse(
        analysis_id=analysis.id,
        document_name=analysis.document.filename_original,
        document_id=analysis.document_id,
        status=analysis.status,
        scores=scores,
        risk_level=analysis.risk_level,
        total_corrections=len(corrections),
        corrections_by_category=category_counts,
        corrections_by_severity=severity_counts,
        corrections=corrections,
        final_opinion=analysis.final_opinion,
        analyzed_at=analysis.completed_at,
    )


@router.get(
    "/document/{document_id}",
    response_model=list[AnalysisDetailResponse],
    summary="Análises de um documento",
    description="Retorna todas as análises realizadas sobre um documento.",
)
async def list_document_analyses(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Lista análises de um documento."""
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.corrections))
        .where(Analysis.document_id == document_id)
        .order_by(Analysis.created_at.desc())
    )
    analyses = result.scalars().all()

    return [AnalysisDetailResponse.model_validate(a) for a in analyses]


def _get_current_model() -> str:
    """Retorna o nome do modelo LLM configurado."""
    model_map = {
        "groq": settings.groq_model,
        "gemini": settings.gemini_model,
        "ollama": settings.ollama_model,
    }
    return model_map.get(settings.llm_provider, "unknown")
