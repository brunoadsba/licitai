"""
Serialização de entidades de comparação para respostas da API.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comparison import Comparacao, Fornecedor
from app.schemas.comparison import ComparacaoResponse, FornecedorResponse


async def carregar_fornecedores(
    db: AsyncSession,
    fornecedor_ids: set[uuid.UUID],
) -> dict[uuid.UUID, Fornecedor]:
    """Carrega fornecedores por id em um dict (id → Fornecedor)."""
    if not fornecedor_ids:
        return {}
    result = await db.execute(
        select(Fornecedor).where(Fornecedor.id.in_(fornecedor_ids))
    )
    return {f.id: f for f in result.scalars().all()}


def fornecedores_ordenados(
    fornecedores: dict[uuid.UUID, Fornecedor],
) -> list[FornecedorResponse]:
    """Converte o dict de fornecedores em lista de respostas ordenada por nome."""
    return [
        FornecedorResponse.model_validate(f)
        for f in sorted(fornecedores.values(), key=lambda f: f.nome)
    ]


def resultados_para_dict(comparacao: Comparacao) -> list[dict]:
    """Converte os resultados de uma comparação em dicts da matriz."""
    return [
        {
            "fornecedor_id": str(r.fornecedor_id),
            "regra_id": r.regra_id,
            "status": r.status,
            "motivo": r.motivo,
            "valor_tr": r.valor_tr,
            "valor_proposta": r.valor_proposta,
        }
        for r in comparacao.resultados
    ]


async def montar_comparacao_response(
    comparacao: Comparacao,
    db: AsyncSession,
    fornecedores_precarregados: dict[uuid.UUID, Fornecedor] | None = None,
) -> ComparacaoResponse:
    """Monta ComparacaoResponse com fornecedores carregados e ordenados.

    `fornecedores_precarregados` evita N+1 quando vários comparacoes são
    serializados em lote: passe um único dict com todos os ids da página.
    """
    if fornecedores_precarregados is not None:
        ids = {r.fornecedor_id for r in comparacao.resultados}
        fornecedores = {i: f for i, f in fornecedores_precarregados.items() if i in ids}
    else:
        fornecedor_ids = {r.fornecedor_id for r in comparacao.resultados}
        fornecedores = await carregar_fornecedores(db, fornecedor_ids)
    return ComparacaoResponse(
        id=comparacao.id,
        tr_document_id=comparacao.tr_document_id,
        molde_id=comparacao.molde_id,
        status=comparacao.status,
        error_message=comparacao.error_message,
        created_at=comparacao.created_at,
        completed_at=comparacao.completed_at,
        total_resultados=len(comparacao.resultados),
        fornecedores=fornecedores_ordenados(fornecedores),
    )
