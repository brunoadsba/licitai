"""
Endpoints para comparação TR × Propostas e matriz de conformidade.

Fluxo:
1. POST /comparison/start — cria comparação (TR + molde + propostas).
2. GET /comparison/{id} — status e resultados parciais.
3. GET /comparison/{id}/matrix — matriz de conformidade regras × fornecedores.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db, async_session_factory
from app.models.document import Document
from app.models.comparison import (
    Molde,
    Fornecedor,
    Comparacao,
    ComparacaoResultado,
)
from app.schemas.comparison import (
    ComparacaoStartResponse,
    ComparacaoResponse,
    FornecedorResponse,
    MatrizResponse,
    FeedbackResponse,
    FeedbackFalha,
)
from app.services.comparator.comparator import comparar
from app.services.comparator.matrix import montar_matriz
from app.services.comparator.feedback import (
    formatar_email_pendencias,
    montar_pendencias,
)
from app.services.email.sender import enviar_email, smtp_configurado
from app.services.rules.loader import parse_molde


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comparison", tags=["Comparação"])


class ComparacaoStartRequest(BaseModel):
    """Payload para iniciar uma comparação."""
    tr_document_id: uuid.UUID
    molde_id: uuid.UUID
    propostas_ids: list[uuid.UUID]


class ComparacaoListResponse(BaseModel):
    """Lista resumida de comparações."""
    comparacoes: list[ComparacaoResponse]
    total: int


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
    """Lista todas as comparações."""
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
        fornecedor_ids = {r.fornecedor_id for r in c.resultados}
        fornecedores = await _carregar_fornecedores(db, fornecedor_ids)
        itens.append(ComparacaoResponse(
            id=c.id,
            tr_document_id=c.tr_document_id,
            molde_id=c.molde_id,
            status=c.status,
            error_message=c.error_message,
            created_at=c.created_at,
            completed_at=c.completed_at,
            total_resultados=len(c.resultados),
            fornecedores=_fornecedores_ordenados(fornecedores),
        ))

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
    """Inicia comparação em background."""
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
        _run_comparacao_background,
        comparacao_id,
        data.tr_document_id,
        data.molde_id,
        data.propostas_ids,
    )

    return ComparacaoStartResponse(
        comparacao_id=comparacao_id,
        message="Comparação iniciada. Acompanhe pelo endpoint de status.",
    )


async def _run_comparacao_background(
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
            itens_tr = _itens_para_dict(tr)

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
                        "itens": _itens_para_dict(doc),
                    })

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


def _itens_para_dict(document: Document) -> list[dict]:
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


async def _carregar_fornecedores(
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


def _fornecedores_ordenados(
    fornecedores: dict[uuid.UUID, Fornecedor],
) -> list[FornecedorResponse]:
    """Converte o dict de fornecedores em lista de respostas ordenada por nome."""
    return [
        FornecedorResponse.model_validate(f)
        for f in sorted(fornecedores.values(), key=lambda f: f.nome)
    ]


def _resultados_para_dict(comparacao: Comparacao) -> list[dict]:
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
    """Retorna status da comparação."""
    result = await db.execute(
        select(Comparacao)
        .options(selectinload(Comparacao.resultados))
        .where(Comparacao.id == comparacao_id)
    )
    comparacao = result.scalar_one_or_none()
    if not comparacao:
        raise HTTPException(status_code=404, detail="Comparação não encontrada.")

    fornecedor_ids = {r.fornecedor_id for r in comparacao.resultados}
    fornecedores = await _carregar_fornecedores(db, fornecedor_ids)

    return ComparacaoResponse(
        id=comparacao.id,
        tr_document_id=comparacao.tr_document_id,
        molde_id=comparacao.molde_id,
        status=comparacao.status,
        error_message=comparacao.error_message,
        created_at=comparacao.created_at,
        completed_at=comparacao.completed_at,
        total_resultados=len(comparacao.resultados),
        fornecedores=_fornecedores_ordenados(fornecedores),
    )


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
    """Retorna a matriz de conformidade."""
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

    fornecedores = await _carregar_fornecedores(db, {
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
        resultados=_resultados_para_dict(comparacao),
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
    """Envia pendências de uma comparação concluída aos fornecedores."""
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
    fornecedores = await _carregar_fornecedores(db, {
        r.fornecedor_id for r in comparacao.resultados
    })
    pendencias_por_fornecedor = montar_pendencias(
        _resultados_para_dict(comparacao), regras_por_id
    )

    tr_nome = comparacao.tr.filename_original if comparacao.tr else ""
    enviados = 0
    falhas: list[FeedbackFalha] = []
    sem_pendencias: list[str] = []
    sem_email: list[str] = []

    for fornecedor_id, fornecedor in fornecedores.items():
        pendencias = pendencias_por_fornecedor.get(str(fornecedor_id), [])
        if not pendencias:
            sem_pendencias.append(fornecedor.nome)
            continue
        if not fornecedor.email:
            sem_email.append(fornecedor.nome)
            continue

        corpo = formatar_email_pendencias(
            fornecedor.nome,
            pendencias,
            tr_nome=tr_nome,
        )
        try:
            await enviar_email(
                to=fornecedor.email,
                subject=f"Pendências de conformidade — {tr_nome or 'Termo de Referência'}",
                body=corpo,
            )
            enviados += 1
        except Exception as e:  # noqa: BLE001 — falha de envio não quebra o lote
            logger.exception(
                "Falha ao enviar e-mail para %s (%s)", fornecedor.nome, fornecedor.email
            )
            falhas.append(FeedbackFalha(
                fornecedor_id=fornecedor.id,
                nome=fornecedor.nome,
                email=fornecedor.email,
                motivo=str(e)[:500],
            ))

    return FeedbackResponse(
        comparacao_id=comparacao.id,
        enviados=enviados,
        falhas=falhas,
        fornecedores_sem_pendencias=sem_pendencias,
        fornecedores_sem_email=sem_email,
    )
