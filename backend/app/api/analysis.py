"""
Endpoints para análise de documentos e geração de relatórios.
"""

import logging
import uuid
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.analysis import Analysis, Correction
from app.models.document import Document, DocumentItem
from app.schemas.analysis import (
    AnalysisDetailResponse,
    AnalysisStartRequest,
    AnalysisStartResponse,
    Art6ChecklistItem,
    CorrectionResponse,
    CorrectionReviewUpdate,
    CorrectedHtmlResponse,
    CorrectedHtmlSkip,
    PendingSummaryItem,
    PendingSummaryResponse,
    ReportResponse,
    ScoreDetail,
    SeiPackEntry,
    SeiPackResponse,
)
from app.services.analyzer.art6_status import build_art6_checklist, summarize_art6_coverage
from app.services.analyzer.corrected_document import (
    build_corrected_docx,
    build_corrected_html,
    build_sei_pack_text,
)
from app.services.jobs import enqueue
from app.services.privacy import (
    CloudPrivacyError,
    assert_cloud_allowed_for_document,
    resolve_classification,
)
from app.utils.metrics import metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Análise"])

PROMPT_VERSION = "v1"


def estimate_tokens(analysis: Analysis) -> int:
    base = (analysis.total_items or 0) * 900 + (analysis.analyzed_items or 0) * 100
    corr = len(getattr(analysis, "corrections", []) or [])
    return base + corr * 350 + 800


def _score_details(analysis: Analysis) -> list[ScoreDetail]:
    """Mapeia as notas da análise preservando zero legítimo (0.0 ≠ ausente)."""
    def _score(value) -> float | None:
        return float(value) if value is not None else None

    return [
        ScoreDetail(label="Nota Geral", score=_score(analysis.score_overall)),
        ScoreDetail(label="Segurança Jurídica", score=_score(analysis.score_juridical)),
        ScoreDetail(label="Qualidade Técnica", score=_score(analysis.score_technical)),
        ScoreDetail(label="Qualidade da Redação", score=_score(analysis.score_writing)),
        ScoreDetail(label="Conformidade Estrutural", score=_score(analysis.score_structural)),
    ]


async def _build_analysis_snapshot(
    db: AsyncSession, document: Document
) -> dict:
    items = (
        await db.execute(
            select(DocumentItem.id).where(
                DocumentItem.document_id == document.id,
                DocumentItem.archived_at.is_(None),
            )
        )
    ).scalars().all()
    return {
        "item_ids": [str(i) for i in items],
        "prompt_version": PROMPT_VERSION,
        "corpus_version": "legal-v1",
        "provider": settings.llm_provider,
        "model": _get_current_model(),
        "analysis_mode": None,  # preenchido pelo caller
    }


@router.post(
    "/{document_id}/start",
    response_model=AnalysisStartResponse,
    status_code=202,
    summary="Iniciar análise",
    description="Inicia a análise completa de um documento usando IA.",
)
async def start_analysis(
    document_id: uuid.UUID,
    payload: AnalysisStartRequest | None = None,
    x_document_classification: str | None = Header(
        default=None, alias="X-Document-Classification"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Enfileira análise na fila durável (processada por `python -m app.worker`)."""
    mode = payload.mode if payload and payload.mode else "economic"
    if mode not in ("multi_agent", "single", "economic"):
        raise HTTPException(
            status_code=422,
            detail="mode inválido. Use: multi_agent, single ou economic.",
        )

    result = await db.execute(
        select(Document).where(Document.id == document_id).with_for_update()
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    if getattr(document, "document_type", "tr") != "tr":
        raise HTTPException(
            status_code=400,
            detail="Somente Termos de Referência podem ser analisados. Propostas usam Comparações.",
        )

    classification = resolve_classification(
        header_value=x_document_classification,
        document_classification=getattr(document, "classification", None),
    )
    try:
        assert_cloud_allowed_for_document(classification)
    except CloudPrivacyError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    if document.status not in ("parsed", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Documento não está pronto para análise. Status atual: {document.status}",
        )

    running = await db.execute(
        select(Analysis).where(
            Analysis.document_id == document_id,
            Analysis.status.in_(["pending", "running"]),
        )
    )
    existing_analysis = running.scalar_one_or_none()
    if existing_analysis:
        if existing_analysis.status == "pending":
            logger.info(
                "Re-enfileirando análise pendente %s (doc %s)",
                existing_analysis.id, document_id,
            )
            job = await enqueue(
                db,
                "analysis",
                {
                    "analysis_id": str(existing_analysis.id),
                    "document_id": str(document_id),
                },
            )
            await db.commit()
            return AnalysisStartResponse(
                analysis_id=existing_analysis.id,
                job_id=job.id,
                message=(
                    "Análise pendente re-enfileirada. "
                    "Requer worker (`python -m app.worker`)."
                ),
            )
        raise HTTPException(
            status_code=409,
            detail="Já existe uma análise em andamento para este documento.",
        )

    snapshot = await _build_analysis_snapshot(db, document)
    snapshot["analysis_mode"] = mode

    analysis = Analysis(
        document_id=document_id,
        status="pending",
        llm_provider=settings.llm_provider,
        llm_model=_get_current_model(),
        analysis_mode=mode,
        total_items=document.total_items,
        run_snapshot=snapshot,
    )
    db.add(analysis)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe uma análise em andamento para este documento.",
        ) from exc

    analysis_id = analysis.id
    job = await enqueue(
        db,
        "analysis",
        {"analysis_id": str(analysis_id), "document_id": str(document_id)},
    )
    await db.commit()

    logger.info(
        "Análise %s enfileirada job=%s (doc %s)", analysis_id, job.id, document_id
    )

    return AnalysisStartResponse(
        analysis_id=analysis_id,
        job_id=job.id,
        message=(
            "Análise enfileirada. Acompanhe pelo status "
            "(worker: `python -m app.worker`)."
        ),
    )


SEI_APPLICABLE_STATUSES = frozenset({"aprovada", "ajustada"})

SEVERITY_RANK = {
    "info": 0,
    "baixo": 1,
    "medio": 2,
    "alto": 3,
    "critico": 4,
}


@router.patch(
    "/corrections/{correction_id}",
    response_model=CorrectionResponse,
    summary="Revisão humana de correção",
    description=(
        "Atualiza review_status de uma correção (aprovada/rejeitada/ajustada/pendente). "
        "Somente aprovada e ajustada liberam cópia para o SEI."
    ),
)
async def update_correction_review(
    correction_id: uuid.UUID,
    payload: CorrectionReviewUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Aplica decisão humana de revisão em uma correção."""
    result = await db.execute(
        select(Correction).where(Correction.id == correction_id)
    )
    correction = result.scalar_one_or_none()
    if not correction:
        raise HTTPException(status_code=404, detail="Correção não encontrada.")

    correction.review_status = payload.review_status
    correction.review_note = payload.review_note
    if payload.review_status == "pendente":
        correction.reviewed_at = None
    else:
        correction.reviewed_at = datetime.now(timezone.utc)

    if payload.review_status == "ajustada":
        if payload.suggested_text is not None:
            correction.suggested_text = payload.suggested_text
        if payload.justification is not None:
            correction.justification = payload.justification

    await db.commit()
    await db.refresh(correction)

    status = payload.review_status
    if status == "aprovada":
        metrics.inc("review_approved")
    elif status == "rejeitada":
        metrics.inc("review_rejected")
    elif status == "ajustada":
        metrics.inc("review_adjusted")

    return CorrectionResponse.model_validate(correction)


def _is_priority_pending(c: Correction) -> bool:
    if getattr(c, "review_status", None) != "pendente":
        return False
    if getattr(c, "category", None) == "estrutural":
        return True
    return SEVERITY_RANK.get(getattr(c, "severity", "") or "", -1) >= SEVERITY_RANK["alto"]


@router.get(
    "/pending-summary",
    response_model=PendingSummaryResponse,
    summary="Pendências prioritárias de revisão",
)
async def pending_summary(db: AsyncSession = Depends(get_db)):
    """Docs com análise concluída e correções pendentes alto/crítico/estrutural."""
    result = await db.execute(
        select(Analysis)
        .options(
            selectinload(Analysis.corrections),
            selectinload(Analysis.document),
        )
        .where(Analysis.status.in_(["completed", "completed_with_errors"]))
        .order_by(Analysis.completed_at.desc())
    )
    analyses = result.scalars().unique().all()
    seen_docs: set[uuid.UUID] = set()
    items: list[PendingSummaryItem] = []
    for analysis in analyses:
        doc_id = analysis.document_id
        if doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)
        pending = [c for c in analysis.corrections if _is_priority_pending(c)]
        if not pending:
            continue
        doc = analysis.document
        items.append(
            PendingSummaryItem(
                document_id=doc_id,
                analysis_id=analysis.id,
                filename=doc.filename_original if doc else "?",
                pending_priority=len(pending),
                status=analysis.status,
            )
        )
    return PendingSummaryResponse(total=len(items), items=items)


def _filter_corrections(
    corrections: list,
    *,
    for_sei: bool = False,
    review_statuses: set[str] | None = None,
    severity_min: str | None = None,
) -> list:
    if for_sei:
        allowed = SEI_APPLICABLE_STATUSES
        items = [c for c in corrections if getattr(c, "review_status", None) in allowed]
    elif review_statuses is not None:
        items = [
            c for c in corrections if getattr(c, "review_status", None) in review_statuses
        ]
    else:
        items = list(corrections)

    if severity_min:
        min_rank = SEVERITY_RANK.get(severity_min)
        if min_rank is None:
            raise HTTPException(
                status_code=422,
                detail="severity_min inválido. Use: info, baixo, medio, alto, critico.",
            )
        items = [
            c
            for c in items
            if SEVERITY_RANK.get(getattr(c, "severity", "") or "", -1) >= min_rank
        ]
    return items


@router.get(
    "/{analysis_id}",
    response_model=AnalysisDetailResponse,
    summary="Status da análise",
    description="Retorna o status e resultados parciais/completos de uma análise.",
)
async def get_analysis(
    analysis_id: uuid.UUID,
    for_sei: bool = False,
    review_status: str | None = None,
    severity_min: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Retorna detalhes da análise com correções (filtro opcional para SEI)."""
    result = await db.execute(
        select(Analysis)
        .options(
            selectinload(Analysis.corrections),
            selectinload(Analysis.document).selectinload(Document.items),
        )
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    resp = AnalysisDetailResponse.model_validate(analysis)
    statuses = (
        {s.strip() for s in review_status.split(",") if s.strip()}
        if review_status
        else None
    )
    filtered = _filter_corrections(
        analysis.corrections,
        for_sei=for_sei,
        review_statuses=statuses,
        severity_min=severity_min,
    )
    if for_sei or statuses is not None or severity_min is not None:
        resp.corrections = [CorrectionResponse.model_validate(c) for c in filtered]
    resp.tokens_estimated = estimate_tokens(analysis)
    items = list(analysis.document.items or []) if analysis.document else []
    checklist_rows = build_art6_checklist(items, analysis.corrections)
    resp.art6_checklist = [Art6ChecklistItem(**row) for row in checklist_rows]
    summary = summarize_art6_coverage(checklist_rows)
    resp.art6_coverage = summary["art6_coverage"]
    resp.art6_meets_target = summary["art6_meets_target"]
    return resp


@router.get(
    "/{analysis_id}/sei-corrections",
    response_model=list[CorrectionResponse],
    summary="Correções aplicáveis ao SEI",
    description="Somente correções com review_status aprovada ou ajustada.",
)
async def get_sei_corrections(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.corrections))
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")
    filtered = _filter_corrections(analysis.corrections, for_sei=True)
    return [CorrectionResponse.model_validate(c) for c in filtered]


@router.get(
    "/{analysis_id}/sei-pack",
    response_model=SeiPackResponse,
    summary="Pacote SEI ordenado",
    description=(
        "Texto consolidado com correções aprovadas/ajustadas, ordenadas por item, "
        "para colar no SEI."
    ),
)
async def get_sei_pack(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis)
        .options(
            selectinload(Analysis.corrections),
            selectinload(Analysis.document).selectinload(Document.items),
        )
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    items_by_id = {item.id: item for item in (analysis.document.items or [])}
    filtered = _filter_corrections(analysis.corrections, for_sei=True)

    def sort_key(c: Correction):
        item = items_by_id.get(c.document_item_id)
        order = (getattr(item, "item_order", 0) or 0) if item else 0
        number = (getattr(item, "item_number", "") or "") if item else ""
        return (order, number, str(c.id))

    entries: list[SeiPackEntry] = []
    entry_dicts: list[dict] = []
    for c in sorted(filtered, key=sort_key):
        item = items_by_id.get(c.document_item_id)
        item_number = getattr(item, "item_number", "?") if item else "?"
        title = getattr(item, "title", None) if item else None
        entry = SeiPackEntry(
            correction_id=c.id,
            item_number=str(item_number),
            title=title,
            suggested_text=c.suggested_text,
            justification=c.justification or "",
            legal_basis=c.legal_basis,
            severity=c.severity,
            category=c.category,
        )
        entries.append(entry)
        entry_dicts.append(entry.model_dump())

    text = build_sei_pack_text(
        document_name=analysis.document.filename_original,
        entries=entry_dicts,
    )
    return SeiPackResponse(
        analysis_id=analysis.id,
        document_id=analysis.document_id,
        document_name=analysis.document.filename_original,
        total=len(entries),
        text=text,
        entries=entries,
    )


@router.get(
    "/{analysis_id}/corrected-html",
    response_model=CorrectedHtmlResponse,
    summary="TR HTML corrigido",
    description=(
        "Documento completo em HTML com replaces DE→PARA das correções "
        "aprovadas/ajustadas."
    ),
)
async def get_corrected_html(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis)
        .options(
            selectinload(Analysis.corrections),
            selectinload(Analysis.document).selectinload(Document.items),
        )
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    if analysis.status not in ("completed", "completed_with_errors"):
        raise HTTPException(
            status_code=409,
            detail="Aguarde a análise concluir antes de exportar o TR corrigido.",
        )

    filtered = _filter_corrections(analysis.corrections, for_sei=True)
    if not filtered:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma correção aprovada ou ajustada para montar o TR corrigido.",
        )

    by_item: dict = {}
    for c in filtered:
        by_item.setdefault(c.document_item_id, []).append(c)

    html_doc, applied, skipped = build_corrected_html(
        filename=analysis.document.filename_original,
        items=list(analysis.document.items or []),
        corrections_by_item=by_item,
    )
    return CorrectedHtmlResponse(
        document_id=analysis.document_id,
        analysis_id=analysis.id,
        document_name=analysis.document.filename_original,
        applied_corrections=len(applied),
        skipped_corrections=[
            CorrectedHtmlSkip(
                correction_id=s["correction_id"],
                reason=s["reason"],
            )
            for s in skipped
            if s.get("correction_id") is not None
        ],
        html=html_doc,
    )


@router.get(
    "/{analysis_id}/corrected-docx",
    summary="TR DOCX corrigido",
    description=(
        "Download .docx com replaces DE→PARA das correções aprovadas/ajustadas."
    ),
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            }
        }
    },
)
async def get_corrected_docx(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis)
        .options(
            selectinload(Analysis.corrections),
            selectinload(Analysis.document).selectinload(Document.items),
        )
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    if analysis.status not in ("completed", "completed_with_errors"):
        raise HTTPException(
            status_code=409,
            detail="Aguarde a análise concluir antes de exportar o TR corrigido.",
        )

    filtered = _filter_corrections(analysis.corrections, for_sei=True)
    if not filtered:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma correção aprovada ou ajustada para montar o TR corrigido.",
        )

    by_item: dict = {}
    for c in filtered:
        by_item.setdefault(c.document_item_id, []).append(c)

    payload, _applied, _skipped = build_corrected_docx(
        filename=analysis.document.filename_original,
        items=list(analysis.document.items or []),
        corrections_by_item=by_item,
    )
    safe_name = "".join(
        ch if ch.isalnum() or ch in ("-", "_", ".") else "_"
        for ch in (analysis.document.filename_original or "tr")
    )
    if not safe_name.lower().endswith(".docx"):
        safe_name = f"{safe_name}.docx"
    return Response(
        content=payload,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Applied-Corrections": str(len(_applied)),
            "X-Skipped-Corrections": str(len(_skipped)),
        },
    )


@router.get(
    "/{analysis_id}/report",
    response_model=ReportResponse,
    summary="Relatório da análise",
    description="Retorna o relatório completo de uma análise finalizada.",
)
async def get_report(
    analysis_id: uuid.UUID,
    for_sei: bool = False,
    severity_min: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Gera relatório consolidado."""
    result = await db.execute(
        select(Analysis)
        .options(
            selectinload(Analysis.corrections),
            selectinload(Analysis.document).selectinload(Document.items),
        )
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    raw = _filter_corrections(
        analysis.corrections,
        for_sei=for_sei,
        severity_min=severity_min,
    )
    corrections = [CorrectionResponse.model_validate(c) for c in raw]

    category_counts = dict(Counter(c.category for c in corrections))
    severity_counts = dict(Counter(c.severity for c in corrections))

    items = list(analysis.document.items or []) if analysis.document else []
    art6_rows = build_art6_checklist(items, analysis.corrections)
    art6 = [Art6ChecklistItem(**row) for row in art6_rows]
    art6_summary = summarize_art6_coverage(art6_rows)

    return ReportResponse(
        analysis_id=analysis.id,
        document_name=analysis.document.filename_original,
        document_id=analysis.document_id,
        status=analysis.status,
        scores=_score_details(analysis),
        risk_level=analysis.risk_level,
        total_corrections=len(corrections),
        corrections_by_category=category_counts,
        corrections_by_severity=severity_counts,
        corrections=corrections,
        final_opinion=analysis.final_opinion,
        analyzed_at=analysis.completed_at,
        tokens_estimated=estimate_tokens(analysis),
        art6_checklist=art6,
        art6_coverage=art6_summary["art6_coverage"],
        art6_meets_target=art6_summary["art6_meets_target"],
    )


@router.post(
    "/{analysis_id}/reanalyze-partial",
    response_model=AnalysisStartResponse,
    status_code=202,
    summary="Reanalisar itens com cobertura incompleta",
)
async def reanalyze_partial(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Enfileira nova análise só dos itens com coverage_errors na análise anterior."""
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.corrections))
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")
    if analysis.status not in ("completed", "completed_with_errors", "error"):
        raise HTTPException(
            status_code=409,
            detail="Aguarde a análise atual concluir antes de reanalisar parcialmente.",
        )

    item_ids: set[str] = set()
    for c in analysis.corrections:
        evidence = getattr(c, "evidence", None) or {}
        if evidence.get("coverage_errors"):
            item_ids.add(str(c.document_item_id))

    if not item_ids:
        raise HTTPException(
            status_code=404,
            detail="Nenhum item com coverage_errors para reanalisar.",
        )

    doc_result = await db.execute(
        select(Document).where(Document.id == analysis.document_id).with_for_update()
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    running = await db.execute(
        select(Analysis).where(
            Analysis.document_id == document.id,
            Analysis.status.in_(["pending", "running"]),
        )
    )
    if running.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Já existe uma análise em andamento para este documento.",
        )

    mode = analysis.analysis_mode or "economic"
    snapshot = await _build_analysis_snapshot(db, document)
    snapshot["analysis_mode"] = mode
    snapshot["only_item_ids"] = sorted(item_ids)

    new_analysis = Analysis(
        document_id=document.id,
        status="pending",
        llm_provider=settings.llm_provider,
        llm_model=_get_current_model(),
        analysis_mode=mode,
        total_items=len(item_ids),
        run_snapshot=snapshot,
    )
    db.add(new_analysis)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe uma análise em andamento para este documento.",
        ) from exc

    job = await enqueue(
        db,
        "analysis",
        {
            "analysis_id": str(new_analysis.id),
            "document_id": str(document.id),
        },
    )
    await db.commit()
    return AnalysisStartResponse(
        analysis_id=new_analysis.id,
        job_id=job.id,
        message=(
            f"Reanálise parcial enfileirada ({len(item_ids)} itens). "
            "Requer worker (`python -m app.worker`)."
        ),
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

    out: list[AnalysisDetailResponse] = []
    for a in analyses:
        resp = AnalysisDetailResponse.model_validate(a)
        resp.tokens_estimated = estimate_tokens(a)
        out.append(resp)
    return out


def _get_current_model() -> str:
    """Retorna o nome do modelo LLM configurado."""
    model_map = {
        "groq": settings.groq_model,
        "gemini": settings.gemini_model,
        "ollama": settings.ollama_model,
    }
    return model_map.get(settings.llm_provider, "unknown")
