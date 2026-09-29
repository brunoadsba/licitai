"""Resposta a partir do parecer e das correções quando o modelo recusa à toa.

Só entra se a recusa for por falta de fonte e o dossiê do TR falar do assunto.
Não inventa artigo de lei.
"""

from __future__ import annotations

from app.schemas.chat import ChatCitation
from app.services.chat.relevance import (
    is_art6_query,
    is_objeto_query,
    is_urgent_query,
    select_for_answer,
)
from app.services.chat.validator import ValidatedAnswer

FALLBACK_REASONS = frozenset(
    {
        "sem-fontes",
        "sem-citacao",
        "recusa-llm",
        "resposta-vazia",
        "resposta-invalida",
        "falha-llm",
    }
)


def aplicar_dossie(
    content: str, fontes: list[ChatCitation], resposta: ValidatedAnswer
) -> tuple[ValidatedAnswer, bool]:
    """Troca recusa vazia (ou resposta só de lei) pelo dossiê do TR, se houver."""
    recusou = resposta.refused and resposta.reason in FALLBACK_REASONS
    if not recusou and not _ignorou_dossie(content, fontes, resposta):
        return resposta, False
    alt = fallback_from_sources(content, fontes)
    if alt is None:
        return resposta, False
    return alt, True


def _ignorou_dossie(
    content: str, fontes: list[ChatCitation], resposta: ValidatedAnswer
) -> bool:
    """Pergunta sobre o TR que o modelo respondeu só com artigo de lei."""
    if resposta.refused:
        return False
    if not (
        is_objeto_query(content) or is_art6_query(content) or is_urgent_query(content)
    ):
        return False
    dossier = {
        f.source_id
        for f in fontes
        if f.source_id and f.type in {"document_item", "correction", "analysis"}
    }
    if not dossier:
        return False
    cited = {c.source_id for c in resposta.citations if c.source_id}
    return cited.isdisjoint(dossier)


def fallback_from_sources(
    query: str, fontes: list[ChatCitation]
) -> ValidatedAnswer | None:
    picked = select_for_answer(query, fontes)
    if not picked:
        return None
    return ValidatedAnswer(
        content=_texto(query, picked),
        grounded=True,
        confidence=0.55,
        citations=picked,
        refused=False,
    )


def _texto(query: str, picked: list[ChatCitation]) -> str:
    if is_urgent_query(query):
        corpo = _lista(
            "As correções mais graves nesta análise são:",
            [f for f in picked if f.type == "correction"] or picked,
        )
    elif is_objeto_query(query):
        tem_correcao = any(f.type == "correction" for f in picked)
        intro = (
            "Sobre o objeto, a análise aponta:"
            if tem_correcao
            else "Ainda não há correção jurídica gravada sobre o objeto. O texto do TR diz:"
        )
        corpo = _lista(intro, picked)
    elif is_art6_query(query):
        corpo = _lista(
            "Sobre o art. 6º, o que esta análise registra neste TR:",
            picked,
        )
    else:
        corpo = _lista("Com o que está neste TR e nesta análise:", picked)

    item = next((f for f in picked if f.type == "document_item"), None)
    onde = ""
    if item:
        onde = f"\n\n**Onde está no TR**\n{item.reference} — {item.title}".rstrip(" —")
    if any(f.type == "correction" for f in picked):
        acao = (
            "Abra a correção citada, confira o trecho no documento "
            "e só então aprove ou ajuste."
        )
    else:
        acao = (
            "Leia o item citado no TR. Quando a análise gravar correções, "
            "pergunte de novo para cruzar o objeto com o que foi apontado."
        )
    return (
        f"**Resposta**\n{corpo}\n\n"
        "**O que fazer agora**\n"
        f"{acao} Se a lei não aparecer nas fontes, "
        "não trate o número de artigo como confirmado."
        f"{onde}"
    )


def _lista(intro: str, fontes: list[ChatCitation]) -> str:
    linhas = [intro]
    for fonte in fontes[:3]:
        detalhe = (fonte.snippet or "").strip()
        if len(detalhe) > 220:
            detalhe = detalhe[:217].rstrip() + "..."
        titulo = (fonte.title or fonte.reference).strip()
        if detalhe:
            linhas.append(f"- {titulo}. {detalhe}")
        else:
            linhas.append(f"- {titulo}.")
    return "\n".join(linhas)
