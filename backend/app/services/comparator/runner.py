"""
Execução assíncrona da comparação TR × propostas.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session_factory
from app.models.comparison import Comparacao, ComparacaoResultado, Molde
from app.models.document import Document
from app.services.comparator.comparator import comparar
from app.services.rules.loader import parse_molde

logger = logging.getLogger(__name__)


def itens_para_dict(document: Document) -> list[dict]:
    """Converte os itens do documento em dicts usados pelo comparador."""
    return [
        {
            "item_number": item.item_number,
            "title": item.title,
            "content": item.content,
            "page_number": item.page_number,
            "item_type": item.item_type,
        }
        for item in document.items
    ]


async def executar_comparacao_background(
    comparacao_id: uuid.UUID,
    tr_document_id: uuid.UUID,
    molde_id: uuid.UUID,
    propostas_ids: list[uuid.UUID],
) -> None:
    """Executa a comparação em background com sessão própria."""
    async with async_session_factory() as db:
        try:
            comparacao = await db.get(Comparacao, comparacao_id)
            if not comparacao:
                logger.error("Comparação %s não encontrada", comparacao_id)
                return
            comparacao.status = "running"
            await db.commit()

            # Carregar dados necessários
            molde = await db.get(Molde, molde_id)
            if not molde:
                raise RuntimeError("Molde não encontrado durante a execução.")
            config = parse_molde(molde.config_json)
            regras = [r.model_dump() for r in config.regras]

            tr_result = await db.execute(
                select(Document)
                .options(selectinload(Document.items))
                .where(Document.id == tr_document_id)
            )
            tr = tr_result.scalar_one_or_none()
            if not tr:
                raise RuntimeError("TR não encontrado durante a execução.")
            itens_tr = itens_para_dict(tr)

            propostas = []
            for pid in propostas_ids:
                doc_result = await db.execute(
                    select(Document)
                    .options(selectinload(Document.items))
                    .where(Document.id == pid)
                )
                doc = doc_result.scalar_one_or_none()
                if doc:
                    propostas.append({
                        "fornecedor_id": doc.fornecedor_id,
                        "itens": itens_para_dict(doc),
                    })
                else:
                    logger.warning(
                        "Proposta %s não encontrada durante a comparação %s; ignorada.",
                        pid, comparacao_id,
                    )

            resultados = await comparar(regras, itens_tr, propostas)

            for r in resultados:
                db.add(ComparacaoResultado(
                    comparacao_id=comparacao_id,
                    fornecedor_id=r["fornecedor_id"],
                    regra_id=r["regra_id"],
                    status=r["status"],
                    motivo=r["motivo"],
                    valor_tr=r["valor_tr"],
                    valor_proposta=r["valor_proposta"],
                ))

            comparacao.status = "completed"
            comparacao.completed_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception:
            logger.exception("Erro na comparação %s", comparacao_id)
            await db.rollback()
            try:
                comparacao = await db.get(Comparacao, comparacao_id)
                if comparacao:
                    comparacao.status = "error"
                    comparacao.error_message = "Erro interno durante a comparação."
                    await db.commit()
            except Exception:
                logger.exception("Erro ao atualizar status da comparação %s", comparacao_id)
