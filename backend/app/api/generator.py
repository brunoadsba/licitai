"""
Endpoints para Geração Assistida de Termos de Referência.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.generator import TRGeneratorRequest, TRGeneratorResponse
from app.services.generator.tr_builder import generate_tr_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generator", tags=["Geração Assistida de TR"])


@router.post(
    "/tr",
    response_model=TRGeneratorResponse,
    status_code=201,
    summary="Gerar Termo de Referência com IA",
    description="Cria um Termo de Referência estruturado completo com base nos parâmetros e na jurisprudência do TCU/RILC.",
)
async def create_tr(
    request: TRGeneratorRequest,
    db: AsyncSession = Depends(get_db),
):
    """Gera um TR completo e o registra na base de documentos."""
    try:
        return await generate_tr_document(request, db)
    except Exception as e:
        logger.exception("Erro ao gerar TR")
        raise HTTPException(
            status_code=500,
            detail="Erro interno durante a geração do Termo de Referência.",
        ) from e
