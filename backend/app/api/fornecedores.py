"""
Endpoints CRUD para fornecedores.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.comparison import Fornecedor
from app.models.document import Document
from app.schemas.comparison import (
    FornecedorCreate,
    FornecedorResponse,
    FornecedorListResponse,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fornecedores", tags=["Fornecedores"])


@router.post(
    "",
    response_model=FornecedorResponse,
    status_code=201,
    summary="Cadastrar fornecedor",
    description="Cadastra um fornecedor que participará da licitação.",
)
async def create_fornecedor(
    data: FornecedorCreate,
    db: AsyncSession = Depends(get_db),
):
    """Cadastra um fornecedor."""
    fornecedor = Fornecedor(
        nome=data.nome,
        cnpj=data.cnpj,
        email=data.email,
    )
    db.add(fornecedor)
    await db.commit()
    await db.refresh(fornecedor)
    return FornecedorResponse.model_validate(fornecedor)


@router.get(
    "",
    response_model=FornecedorListResponse,
    summary="Listar fornecedores",
    description="Retorna todos os fornecedores cadastrados.",
)
async def list_fornecedores(
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os fornecedores."""
    result = await db.execute(
        select(Fornecedor).order_by(Fornecedor.nome)
    )
    fornecedores = result.scalars().all()
    return FornecedorListResponse(
        fornecedores=[
            FornecedorResponse.model_validate(f) for f in fornecedores
        ],
        total=len(fornecedores),
    )


@router.get(
    "/{fornecedor_id}",
    response_model=FornecedorResponse,
    summary="Detalhes do fornecedor",
    description="Retorna um fornecedor pelo id.",
)
async def get_fornecedor(
    fornecedor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retorna um fornecedor."""
    result = await db.execute(
        select(Fornecedor).where(Fornecedor.id == fornecedor_id)
    )
    fornecedor = result.scalar_one_or_none()
    if not fornecedor:
        raise HTTPException(
            status_code=404, detail="Fornecedor não encontrado."
        )
    return FornecedorResponse.model_validate(fornecedor)


@router.put(
    "/{fornecedor_id}",
    response_model=FornecedorResponse,
    summary="Atualizar fornecedor",
    description="Atualiza os dados de um fornecedor.",
)
async def update_fornecedor(
    fornecedor_id: uuid.UUID,
    data: FornecedorCreate,
    db: AsyncSession = Depends(get_db),
):
    """Atualiza um fornecedor."""
    result = await db.execute(
        select(Fornecedor).where(Fornecedor.id == fornecedor_id)
    )
    fornecedor = result.scalar_one_or_none()
    if not fornecedor:
        raise HTTPException(
            status_code=404, detail="Fornecedor não encontrado."
        )
    fornecedor.nome = data.nome
    fornecedor.cnpj = data.cnpj
    fornecedor.email = data.email
    await db.commit()
    await db.refresh(fornecedor)
    return FornecedorResponse.model_validate(fornecedor)


@router.delete(
    "/{fornecedor_id}",
    status_code=204,
    summary="Remover fornecedor",
    description="Remove um fornecedor sem documentos vinculados.",
)
async def delete_fornecedor(
    fornecedor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Remove um fornecedor."""
    result = await db.execute(
        select(Fornecedor).where(Fornecedor.id == fornecedor_id)
    )
    fornecedor = result.scalar_one_or_none()
    if not fornecedor:
        raise HTTPException(
            status_code=404, detail="Fornecedor não encontrado."
        )

    # Impede exclusão quando existem propostas vinculadas (integridade)
    doc_result = await db.execute(
        select(Document.id)
        .where(Document.fornecedor_id == fornecedor_id)
        .limit(1)
    )
    if doc_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=(
                "Não é possível remover este fornecedor: existem propostas "
                "vinculadas. Remova as propostas primeiro."
            ),
        )

    await db.delete(fornecedor)
    await db.commit()
