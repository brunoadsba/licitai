"""
Endpoints CRUD para moldes de regras (config_json).
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.comparison import Molde, Comparacao
from app.models.document import Document
from app.schemas.comparison import (
    MoldeCreate,
    MoldeResponse,
    MoldeListResponse,
)
from app.services.rules.loader import parse_molde
from app.services.rules.extractor import extrair_valor


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/moldes", tags=["Moldes"])


@router.post(
    "",
    response_model=MoldeResponse,
    status_code=201,
    summary="Criar molde",
    description="Cria um molde de regras validando o config_json.",
)
async def create_molde(
    data: MoldeCreate,
    db: AsyncSession = Depends(get_db),
):
    """Cria um molde após validar o JSON de regras."""
    try:
        parse_molde(data.config_json)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"config_json inválido: {exc.errors()[:3]}",
        )

    molde = Molde(
        nome=data.nome,
        descricao=data.descricao,
        config_json=data.config_json,
    )
    db.add(molde)
    await db.commit()
    await db.refresh(molde)
    return MoldeResponse.model_validate(molde)


@router.get(
    "",
    response_model=MoldeListResponse,
    summary="Listar moldes",
    description="Retorna todos os moldes cadastrados.",
)
async def list_moldes(
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os moldes."""
    result = await db.execute(
        select(Molde).order_by(Molde.created_at.desc())
    )
    moldes = result.scalars().all()
    return MoldeListResponse(
        moldes=[MoldeResponse.model_validate(m) for m in moldes],
        total=len(moldes),
    )


@router.get(
    "/{molde_id}",
    response_model=MoldeResponse,
    summary="Detalhes do molde",
    description="Retorna um molde pelo id.",
)
async def get_molde(
    molde_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retorna um molde."""
    result = await db.execute(
        select(Molde).where(Molde.id == molde_id)
    )
    molde = result.scalar_one_or_none()
    if not molde:
        raise HTTPException(status_code=404, detail="Molde não encontrado.")
    return MoldeResponse.model_validate(molde)


@router.put(
    "/{molde_id}",
    response_model=MoldeResponse,
    summary="Atualizar molde",
    description="Atualiza nome, descrição ou regras de um molde.",
)
async def update_molde(
    molde_id: uuid.UUID,
    data: MoldeCreate,
    db: AsyncSession = Depends(get_db),
):
    """Atualiza um molde validando o novo config_json."""
    result = await db.execute(
        select(Molde).where(Molde.id == molde_id)
    )
    molde = result.scalar_one_or_none()
    if not molde:
        raise HTTPException(status_code=404, detail="Molde não encontrado.")

    try:
        parse_molde(data.config_json)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"config_json inválido: {exc.errors()[:3]}",
        )

    molde.nome = data.nome
    molde.descricao = data.descricao
    molde.config_json = data.config_json
    await db.commit()
    await db.refresh(molde)
    return MoldeResponse.model_validate(molde)


@router.delete(
    "/{molde_id}",
    status_code=204,
    summary="Remover molde",
    description="Remove um molde sem comparações vinculadas.",
)
async def delete_molde(
    molde_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Remove um molde."""
    result = await db.execute(
        select(Molde).where(Molde.id == molde_id)
    )
    molde = result.scalar_one_or_none()
    if not molde:
        raise HTTPException(status_code=404, detail="Molde não encontrado.")

    # Impede exclusão quando existem comparações vinculadas (integridade)
    cmp_result = await db.execute(
        select(Comparacao.id).where(Comparacao.molde_id == molde_id).limit(1)
    )
    if cmp_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=(
                "Não é possível remover este molde: existem comparações "
                "vinculadas. Remova as comparações primeiro."
            ),
        )

    await db.delete(molde)
    await db.commit()


@router.post(
    "/{molde_id}/duplicate",
    response_model=MoldeResponse,
    status_code=201,
    summary="Duplicar molde",
    description="Cria uma cópia de um molde existente.",
)
async def duplicate_molde(
    molde_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Clona um molde existente com sufixo (Cópia)."""
    result = await db.execute(
        select(Molde).where(Molde.id == molde_id)
    )
    molde = result.scalar_one_or_none()
    if not molde:
        raise HTTPException(status_code=404, detail="Molde não encontrado.")

    novo_molde = Molde(
        nome=f"{molde.nome} (Cópia)",
        descricao=molde.descricao,
        config_json=molde.config_json,
    )
    db.add(novo_molde)
    await db.commit()
    await db.refresh(novo_molde)
    return MoldeResponse.model_validate(novo_molde)


@router.post(
    "/{molde_id}/validate/{document_id}",
    summary="Validar molde contra documento (Dry-Run)",
    description="Testa a extração das regras de um molde sobre um documento TR sem salvar a comparação.",
)
async def validate_molde_dry_run(
    molde_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Executa a extração em memória (dry-run) e mostra quais regras capturaram valor."""
    m_result = await db.execute(select(Molde).where(Molde.id == molde_id))
    molde = m_result.scalar_one_or_none()
    if not molde:
        raise HTTPException(status_code=404, detail="Molde não encontrado.")

    d_result = await db.execute(
        select(Document)
        .options(selectinload(Document.items))
        .where(Document.id == document_id)
    )
    document = d_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    config = parse_molde(molde.config_json)
    itens_dict = [
        {"item_number": i.item_number, "title": i.title or "", "content": i.content or ""}
        for i in document.items
    ]

    resultados_dry_run = []
    encontrados = 0

    for regra in config.regras:
        regra_dict = regra.model_dump()
        valor = extrair_valor(regra_dict, itens_dict)
        tem_valor = valor is not None
        if tem_valor:
            encontrados += 1

        resultados_dry_run.append({
            "regra_id": regra.id,
            "rotulo": regra.rotulo,
            "tipo": regra.tipo,
            "ancora": regra.ancora,
            "valor_extraido": str(valor) if valor is not None else None,
            "encontrado": tem_valor,
        })

    return {
        "molde_id": molde_id,
        "molde_nome": molde.nome,
        "documento_id": document_id,
        "documento_nome": document.filename_original,
        "total_regras": len(config.regras),
        "regras_encontradas": encontrados,
        "resultados": resultados_dry_run,
    }
