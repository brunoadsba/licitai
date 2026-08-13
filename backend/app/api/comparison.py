"""
Endpoints para comparação TR × Propostas e matriz de conformidade.

Fluxo:
1. POST /comparison/start — cria comparação (TR + molde + propostas).
2. GET /comparison/{id} — status e resultados parciais.
3. GET /comparison/{id}/matrix — matriz de conformidade regras × fornecedores.
"""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.comparison import Comparacao, Molde
from app.models.document import Document
from app.schemas.comparison import (
    ComparacaoListResponse,
    ComparacaoResponse,
    ComparacaoStartRequest,
    ComparacaoStartResponse,
    MatrizResponse,
    FeedbackResponse,
)
from app.services.comparator.feedback import enviar_pendencias_por_email
from app.services.comparator.matrix import montar_matriz
from app.services.comparator.runner import executar_comparacao_background
from app.services.comparator.serializers import (
    carregar_fornecedores,
    montar_comparacao_response,
    resultados_para_dict,
)
from app.services.email.sender import smtp_configurado
from app.services.rules.loader import parse_molde

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

    itens = []
    for c in comparacoes:
        itens.append(await montar_comparacao_response(c, db))

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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Validar TR
    tr = await db.get(Document, data.tr_document_id)
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
    propostas = []
    for pid in data.propostas_ids:
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
        propostas.append(doc)

    comparacao = Comparacao(
        tr_document_id=data.tr_document_id,
        molde_id=data.molde_id,
        status="pending",
    )
    db.add(comparacao)
    await db.flush()
    comparacao_id = comparacao.id
    await db.commit()

    background_tasks.add_task(
        executar_comparacao_background,
        comparacao_id,
        data.tr_document_id,
        data.molde_id,
        data.propostas_ids,
    )

    return ComparacaoStartResponse(
        comparacao_id=comparacao_id,
        message="Comparação iniciada. Acompanhe pelo endpoint de status.",
    )


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


@router.get(
    "/{comparacao_id}/matrix",
    response_model=MatrizResponse,
    summary="Matriz de conformidade",
    description="Retorna a matriz de conformidade regras × fornecedores.",
)
async def get_matrix(
    comparacao_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Comparacao)
        .options(
            selectinload(Comparacao.resultados),
            selectinload(Comparacao.molde),
        )
        .where(Comparacao.id == comparacao_id)
    )
    comparacao = result.scalar_one_or_none()
    if not comparacao:
        raise HTTPException(status_code=404, detail="Comparação não encontrada.")

    config = parse_molde(comparacao.molde.config_json)
    regras = [{"id": r.id, "rotulo": r.rotulo} for r in config.regras]

    fornecedores = await carregar_fornecedores(db, {
        r.fornecedor_id for r in comparacao.resultados
    })
    fornecedores_matriz = [
        {
            "id": f.id,
            "nome": f.nome,
            "cnpj": f.cnpj,
            "email": f.email,
            "created_at": f.created_at,
        }
        for f in sorted(fornecedores.values(), key=lambda f: f.nome)
    ]

    return montar_matriz(
        comparacao_id=str(comparacao.id),
        tr_document_id=str(comparacao.tr_document_id),
        status=comparacao.status,
        regras=regras,
        fornecedores=fornecedores_matriz,
        resultados=resultados_para_dict(comparacao),
    )


@router.post(
    "/{comparacao_id}/feedback",
    response_model=FeedbackResponse,
    summary="Enviar pendências por e-mail",
    description=(
        "Envia um e-mail a cada fornecedor com e-mail cadastrado listando as "
        "pendências (falhas/atenções) identificadas na comparação. Falhas de "
        "envio são reportadas no retorno sem quebrar a operação."
    ),
)
async def send_feedback(
    comparacao_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Comparacao)
        .options(
            selectinload(Comparacao.resultados),
            selectinload(Comparacao.molde),
            selectinload(Comparacao.tr),
        )
        .where(Comparacao.id == comparacao_id)
    )
    comparacao = result.scalar_one_or_none()
    if not comparacao:
        raise HTTPException(status_code=404, detail="Comparação não encontrada.")
    if comparacao.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Comparação não concluída. Status atual: {comparacao.status}",
        )
    if not smtp_configurado():
        raise HTTPException(
            status_code=400,
            detail=(
                "SMTP não configurado. Defina SMTP_HOST e SMTP_FROM no .env "
                "para habilitar o envio de pendências."
            ),
        )

    # Rótulos das regras do molde
    config = parse_molde(comparacao.molde.config_json)
    regras_por_id = {r.id: r.rotulo for r in config.regras}

    # Fornecedores envolvidos
    fornecedores = await carregar_fornecedores(db, {
        r.fornecedor_id for r in comparacao.resultados
    })

    tr_nome = comparacao.tr.filename_original if comparacao.tr else ""
    enviados, falhas, sem_pendencias, sem_email = (
        await enviar_pendencias_por_email(
            comparacao, regras_por_id, fornecedores, tr_nome
        )
    )

    return FeedbackResponse(
        comparacao_id=comparacao.id,
        enviados=enviados,
        falhas=falhas,
        fornecedores_sem_pendencias=sem_pendencias,
        fornecedores_sem_email=sem_email,
    )