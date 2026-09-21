"""
Endpoints para comparação TR × Propostas e matriz de conformidade.

Fluxo:
1. POST /comparison/start — cria comparação (TR + molde + propostas).
2. GET /comparison/{id} — status e resultados parciais.
3. GET /comparison/{id}/matrix — matriz de conformidade regras × fornecedores.
"""

import hashlib
import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.comparison import Comparacao, Molde
from app.models.document import Document, DocumentItem
from app.schemas.comparison import (
    ComparacaoListResponse,
    ComparacaoResponse,
    ComparacaoStartRequest,
    ComparacaoStartResponse,
)
from app.services.comparator.serializers import (
    carregar_fornecedores,
    montar_comparacao_response,
)
from app.services.jobs import enqueue
from app.utils import idempotency as idempotency_cache
from app.utils.request_context import request_id_var

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comparison", tags=["Comparação"])


@router.get(
    "",
    response_model=ComparacaoListResponse,
    summary="Listar comparações",
    description="Retorna todas as comparações, ordenadas por data.",
)
async def list_comparacoes(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    total = (
        await db.execute(select(func.count()).select_from(Comparacao))
    ).scalar_one()
    result = await db.execute(
        select(Comparacao)
        .options(selectinload(Comparacao.resultados))
        .order_by(Comparacao.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    comparacoes = result.scalars().all()

    # Uma única query de fornecedores para a página inteira (evita N+1).
    todos_ids = {
        r.fornecedor_id
        for c in comparacoes
        for r in c.resultados
    }
    fornecedores_pagina = await carregar_fornecedores(db, todos_ids)

    itens = [
        await montar_comparacao_response(c, db, fornecedores_pagina)
        for c in comparacoes
    ]

    return ComparacaoListResponse(comparacoes=itens, total=total)


@router.post(
    "/start",
    response_model=ComparacaoStartResponse,
    status_code=202,
    summary="Iniciar comparação",
    description="Inicia a comparação entre TR e propostas usando um molde.",
)
async def start_comparacao(
    data: ComparacaoStartRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
):
    if idempotency_key:
        cached = idempotency_cache.lookup(
            f"comparacao:{data.tr_document_id}:{data.molde_id}:{idempotency_key}"
        )
        if cached:
            logger.info(
                "comparison.start.idempotent_hit tr=%s request_id=%s",
                data.tr_document_id, request_id_var.get(),
            )
            return ComparacaoStartResponse(**cached)
    # Lock serializa starts concorrentes do mesmo TR (TOCTOU); no-op no SQLite.
    tr = await db.get(Document, data.tr_document_id, with_for_update=True)
    if not tr:
        raise HTTPException(status_code=404, detail="TR não encontrado.")
    if tr.document_type != "tr":
        raise HTTPException(
            status_code=400, detail="O documento informado não é um TR."
        )
    if tr.status not in ("parsed", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"TR não está pronto. Status atual: {tr.status}",
        )

    # Validar molde
    molde = await db.get(Molde, data.molde_id)
    if not molde:
        raise HTTPException(status_code=404, detail="Molde não encontrado.")

    # Validar propostas
    if not data.propostas_ids:
        raise HTTPException(
            status_code=400, detail="Informe ao menos uma proposta."
        )

    # Dedupe preservando ordem: duplicatas violariam uq_comparacao_fornecedor_regra.
    propostas_ids_unicas = list(dict.fromkeys(data.propostas_ids))
    if len(propostas_ids_unicas) < len(data.propostas_ids):
        logger.warning(
            "comparison.start.propostas_duplicadas total_informado=%d unico=%d",
            len(data.propostas_ids), len(propostas_ids_unicas),
        )

    propostas = []
    fornecedores_vistos: set[uuid.UUID] = set()
    for pid in propostas_ids_unicas:
        doc = await db.get(Document, pid)
        if not doc or doc.document_type != "proposta":
            raise HTTPException(
                status_code=400,
                detail=f"Proposta {pid} não encontrada ou não é uma proposta.",
            )
        if doc.fornecedor_id is None:
            raise HTTPException(
                status_code=400,
                detail=f"Proposta {pid} não está vinculada a um fornecedor.",
            )
        if doc.fornecedor_id in fornecedores_vistos:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cada fornecedor pode ter apenas uma proposta por "
                    "comparação (fornecedor "
                    f"{doc.fornecedor_id} possui mais de uma proposta selecionada)."
                ),
            )
        fornecedores_vistos.add(doc.fornecedor_id)
        propostas.append(doc)

    tr_item_ids = (
        await db.execute(
            select(DocumentItem.id).where(
                DocumentItem.document_id == data.tr_document_id,
                DocumentItem.archived_at.is_(None),
            )
        )
    ).scalars().all()
    molde_hash = hashlib.sha256(molde.config_json.encode("utf-8")).hexdigest()
    model_map = {
        "groq": settings.groq_model,
        "gemini": settings.gemini_model,
        "ollama": settings.ollama_model,
    }
    run_snapshot = {
        "item_ids": [str(i) for i in tr_item_ids],
        "molde_config_hash": molde_hash,
        "prompt_version": "comparison-v1",
        "corpus_version": "legal-v2",
        "provider": settings.llm_provider,
        "model": model_map.get(settings.llm_provider, "unknown"),
        "propostas_ids": [str(p) for p in propostas_ids_unicas],
    }

    comparacao = Comparacao(
        tr_document_id=data.tr_document_id,
        molde_id=data.molde_id,
        status="pending",
        run_snapshot=run_snapshot,
        propostas_ids=[str(p) for p in propostas_ids_unicas],
    )
    db.add(comparacao)
    await db.flush()
    comparacao_id = comparacao.id

    job = await enqueue(
        db,
        "comparacao",
        {
            "comparacao_id": str(comparacao_id),
            "tr_document_id": str(data.tr_document_id),
            "molde_id": str(data.molde_id),
            "propostas_ids": [str(p) for p in propostas_ids_unicas],
        },
    )
    await db.commit()

    logger.info(
        "comparison.start.enqueued id=%s request_id=%s",
        comparacao_id, request_id_var.get(),
    )
    resp = ComparacaoStartResponse(
        comparacao_id=comparacao_id,
        job_id=job.id,
        message=(
            "Comparação enfileirada. Acompanhe pelo status "
            "(worker: `python -m app.worker`)."
        ),
    )
    if idempotency_key:
        idempotency_cache.store(
            f"comparacao:{data.tr_document_id}:{data.molde_id}:{idempotency_key}",
            {"comparacao_id": comparacao_id, "job_id": job.id, "message": resp.message},
        )
    return resp


@router.get(
    "/{comparacao_id}",
    response_model=ComparacaoResponse,
    summary="Status da comparação",
    description="Retorna o status e totais de uma comparação.",
)
async def get_comparacao(
    comparacao_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Comparacao)
        .options(selectinload(Comparacao.resultados))
        .where(Comparacao.id == comparacao_id)
    )
    comparacao = result.scalar_one_or_none()
    if not comparacao:
        raise HTTPException(status_code=404, detail="Comparação não encontrada.")

    return await montar_comparacao_response(comparacao, db)