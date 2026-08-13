"""
Geração de pendências por fornecedor (RF04 — Fase 3.2).

Agrega os resultados `falha`/`atencao` de uma comparação por fornecedor e
monta o texto legível em PT-BR para envio por e-mail (regra, rótulo, valor
esperado no TR e valor proposto).
"""

import logging
import uuid

from app.models.comparison import Comparacao, Fornecedor
from app.schemas.comparison import FeedbackFalha
from app.services.email.sender import enviar_email

logger = logging.getLogger(__name__)

STATUS_DESCRICOES = {
    "falha": "NÃO CONFORME",
    "atencao": "ATENÇÃO",
}


def _valor_legivel(valor) -> str:
    """Converte um valor extraído em texto legível."""
    if valor is None or valor == "":
        return "não informado"
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    return str(valor)


def montar_pendencias(
    resultados: list[dict],
    regras_por_id: dict[str, str],
) -> dict[str, list[dict]]:
    """
    Agrega resultados `falha`/`atencao` por fornecedor.

    Args:
        resultados: lista de dicts com `fornecedor_id`, `regra_id`, `status`,
            `motivo`, `valor_tr`, `valor_proposta`.
        regras_por_id: mapa `regra_id` → rótulo legível da regra.

    Returns:
        Dict `{fornecedor_id: [pendência, ...]}`. Cada pendência tem:
        `regra_id`, `rotulo`, `status`, `motivo`, `valor_tr`, `valor_proposta`.
    """
    pendencias: dict[str, list[dict]] = {}
    for r in resultados:
        status = r.get("status")
        if status not in ("falha", "atencao"):
            continue
        regra_id = r.get("regra_id", "")
        fornecedor_id = str(r.get("fornecedor_id"))
        pendencias.setdefault(fornecedor_id, []).append({
            "regra_id": regra_id,
            "rotulo": regras_por_id.get(regra_id, regra_id),
            "status": status,
            "motivo": r.get("motivo") or "",
            "valor_tr": _valor_legivel(r.get("valor_tr")),
            "valor_proposta": _valor_legivel(r.get("valor_proposta")),
        })
    return pendencias


def formatar_email_pendencias(
    fornecedor_nome: str,
    pendencias: list[dict],
    tr_nome: str = "",
) -> str:
    """
    Monta o corpo do e-mail (texto simples) com as pendências de um fornecedor.
    """
    linhas = []
    if tr_nome:
        linhas.append(f"Referente à contratação: {tr_nome}")
        linhas.append("")
    linhas.append(f"Prezado(a) {fornecedor_nome},")
    linhas.append("")
    linhas.append(
        "Durante a análise de conformidade da proposta em relação ao Termo de "
        "Referência, foram identificadas pendências que exigem atenção:"
    )
    linhas.append("")

    for i, p in enumerate(pendencias, 1):
        descricao = STATUS_DESCRICOES.get(p["status"], p["status"].upper())
        linhas.append(f"{i}. {p['rotulo']} — {descricao}")
        if p["motivo"]:
            linhas.append(f"   Motivo: {p['motivo']}")
        linhas.append(f"   Esperado no TR: {p['valor_tr']}")
        linhas.append(f"   Consta na proposta: {p['valor_proposta']}")
        linhas.append("")

    linhas.append(
        "Solicitamos a regularização das pendências no prazo indicado no edital."
    )
    return "\n".join(linhas).strip()


async def enviar_pendencias_por_email(
    comparacao: Comparacao,
    regras_por_id: dict[str, str],
    fornecedores: dict[uuid.UUID, Fornecedor],
    tr_nome: str,
) -> tuple[int, list[FeedbackFalha], list[str], list[str]]:
    """
    Envia e-mail de pendências a cada fornecedor com e-mail cadastrado.

    Returns:
        Tupla (enviados, falhas, sem_pendencias, sem_email). Falhas de envio
        são acumuladas sem interromper o lote.
    """
    pendencias_por_fornecedor = montar_pendencias(
        [
            {
                "fornecedor_id": str(r.fornecedor_id),
                "regra_id": r.regra_id,
                "status": r.status,
                "motivo": r.motivo,
                "valor_tr": r.valor_tr,
                "valor_proposta": r.valor_proposta,
            }
            for r in comparacao.resultados
        ],
        regras_por_id,
    )

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

    return enviados, falhas, sem_pendencias, sem_email
