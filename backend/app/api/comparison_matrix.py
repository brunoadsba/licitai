"""Matriz de conformidade + feedback por e-mail — extraído de `api/comparison.py`."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.comparison import Comparacao
from app.schemas.comparison import (
    FeedbackResponse,
    MatrizResponse,
)
from app.services.comparator.feedback import enviar_pendencias_por_email
from app.services.comparator.matrix import montar_matriz
from app.services.comparator.serializers import (
    carregar_fornecedores,
    resultados_para_dict,
)
from app.services.email.sender import smtp_configurado
from app.services.rules.loader import parse_molde

router = APIRouter(prefix="/comparison", tags=["Comparação"])


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
