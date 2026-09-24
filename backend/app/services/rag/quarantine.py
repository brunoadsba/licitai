"""Quarentena de fontes jurídicas sem comprovação oficial (Fase 0B).

Não apaga o corpus. Itens listados saem da recuperação padrão, de
`legal_basis` e do parecer até existir URL oficial, hash e revisão.
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from dataclasses import dataclass

VERSION_PREFIX = "quarantine"
QUARANTINE_VERSION = "quarantine-0B"

QUARANTINE_ONLY_MESSAGE = (
    "As únicas fontes encontradas para esta consulta estão em quarentena "
    "(jurisprudência TCU sem comprovação oficial). Não posso fundamentar "
    "a resposta nesse material."
)

# law_number exatamente como em ingest_juris_tcu.py — não usar "TCU" genérico
# (o harness de recall usa law_number="TCU" como fixture sintético).
UNVERIFIED_TCU_LAWS = frozenset(
    {
        "Súmula 247/TCU",
        "Súmula 272/TCU",
        "Acórdão 1214/2013-TCU-Plenário",
    }
)

_CITATION_RE = re.compile(
    r"s[úu]mula\s*247|s[úu]mula\s*272|"
    r"ac[óo]rd[aã]o\s*1214\s*/\s*2013|"
    r"1214\s*/\s*2013\s*[- ]\s*tcu",
    re.IGNORECASE,
)

quarantine_only_hit: ContextVar[bool] = ContextVar(
    "rag_quarantine_only_hit", default=False
)


@dataclass(frozen=True)
class QuarantineEntry:
    law_number: str
    title: str
    source_url: str
    reason: str


PENDING_CONFIRMATION: tuple[QuarantineEntry, ...] = (
    QuarantineEntry(
        law_number="Súmula 247/TCU",
        title="Princípio do Parcelamento do Objeto e Competitividade",
        source_url="https://pesquisa.apps.tcu.gov.br/",
        reason="URL genérica da busca TCU; enunciado misturado com comentário da Lei 14.133",
    ),
    QuarantineEntry(
        law_number="Súmula 272/TCU",
        title="Vedação de Marcas e Especificações Exclusivas",
        source_url="https://pesquisa.apps.tcu.gov.br/",
        reason="URL genérica da busca TCU; enunciado misturado com comentário da Lei 14.133",
    ),
    QuarantineEntry(
        law_number="Acórdão 1214/2013-TCU-Plenário",
        title="Critérios de Qualificação Técnica e Exequibilidade",
        source_url="https://pesquisa.apps.tcu.gov.br/",
        reason="URL genérica da busca TCU; atribuição e texto sem fonte específica",
    ),
)


def is_quarantine_version(version: str | None) -> bool:
    return bool(version) and version.lower().startswith(VERSION_PREFIX)


def is_quarantined_law(
    law_number: str | None, version: str | None = None
) -> bool:
    if is_quarantine_version(version):
        return True
    return bool(law_number) and law_number in UNVERIFIED_TCU_LAWS


def cites_quarantined_source(text: str | None) -> bool:
    return bool(text) and bool(_CITATION_RE.search(text))


def sanitize_legal_basis(legal_basis: str | None) -> str | None:
    """None se o fundamento citar fonte em quarentena."""
    if not legal_basis or not legal_basis.strip():
        return None
    if cites_quarantined_source(legal_basis) or is_quarantined_law(legal_basis):
        return None
    return legal_basis


def scrub_quarantined_text(text: str | None) -> str | None:
    """Remove frases que citam material em quarentena; preserva o restante."""
    if not text or not text.strip():
        return text
    if not cites_quarantined_source(text):
        return text
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [p for p in parts if p and not cites_quarantined_source(p)]
    return " ".join(kept).strip() or None


def filter_active_rows(rows: list[dict]) -> tuple[list[dict], int]:
    """Separa linhas ativas; devolve (ativas, quantidade excluída)."""
    active: list[dict] = []
    dropped = 0
    for row in rows:
        if is_quarantined_law(row.get("law_number"), row.get("version")):
            dropped += 1
            continue
        active.append(row)
    quarantine_only_hit.set(dropped > 0 and not active)
    return active, dropped


def consume_quarantine_only() -> bool:
    hit = quarantine_only_hit.get()
    quarantine_only_hit.set(False)
    return hit


def apply_sql_quarantine_filter(
    sql: str, params: dict, alias: str = "ld"
) -> str:
    """Acrescenta exclusão de quarentena a SQL textual."""
    params["qver"] = f"{VERSION_PREFIX}%"
    clauses = [f"COALESCE({alias}.version, '') NOT LIKE :qver"]
    placeholders: list[str] = []
    for i, law in enumerate(sorted(UNVERIFIED_TCU_LAWS)):
        key = f"qlaw{i}"
        placeholders.append(f":{key}")
        params[key] = law
    clauses.append(f"{alias}.law_number NOT IN ({', '.join(placeholders)})")
    return f"{sql} AND {' AND '.join(clauses)}"
