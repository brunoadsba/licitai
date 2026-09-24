"""Classificação estável das normas conhecidas do piloto."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal import LegalDocument
from app.models.legal_versioned import LegalWork
from app.services.rag.quarantine import is_quarantined_law

CATALOG: dict[str, dict[str, str]] = {
    "Lei 14.133/2021": {
        "kind": "lei",
        "issuing_body": "União",
        "sphere": "federal",
        "jurisdiction": "Brasil",
        "subject_area": "licitacoes",
    },
    "Lei 13.303/2016": {
        "kind": "lei",
        "issuing_body": "União",
        "sphere": "federal",
        "jurisdiction": "Brasil",
        "subject_area": "estatais",
    },
    "RILC CODEBA": {
        "kind": "regulamento",
        "issuing_body": "CODEBA",
        "sphere": "empresa",
        "jurisdiction": "Bahia",
        "subject_area": "licitacoes",
    },
}


def classify_work(law_number: str, law_title: str = "") -> dict[str, str | None]:
    if law_number in CATALOG:
        return dict(CATALOG[law_number])
    if "RILC" in law_number.upper():
        return dict(CATALOG["RILC CODEBA"])
    if "TCU" in law_number.upper() or "Súmula" in law_number or "Sumula" in law_number:
        return {
            "kind": "jurisprudencia",
            "issuing_body": "TCU",
            "sphere": "federal",
            "jurisdiction": "Brasil",
            "subject_area": "licitacoes",
        }
    return {
        "kind": "lei",
        "issuing_body": None,
        "sphere": None,
        "jurisdiction": None,
        "subject_area": None,
        "title_hint": law_title,
    }


def may_publish_work(law_number: str, version: str | None) -> bool:
    return not is_quarantined_law(law_number, version)


SEARCH_LAW: dict[str, str] = {
    "Lei 14.133/2021": "14.133",
    "Lei 13.303/2016": "13.303",
    "RILC CODEBA": "RILC",
}


def _is_ingested(law_number: str, ingested: list[str]) -> bool:
    needle = SEARCH_LAW.get(law_number, law_number).lower()
    key = law_number.lower()
    return any(needle in item.lower() or key in item.lower() for item in ingested)


async def _ingested_law_numbers(db: AsyncSession) -> list[str]:
    works = list((await db.execute(select(LegalWork.law_number))).scalars().all())
    docs = list((await db.execute(select(LegalDocument.law_number))).scalars().all())
    return works + docs


async def list_pilot_sources(db: AsyncSession) -> list[dict]:
    """Inventário do piloto: works + documentos RAG. TCU visível, sem uso na análise."""
    ingested = await _ingested_law_numbers(db)
    sources: list[dict] = []
    for law_number, meta in CATALOG.items():
        present = _is_ingested(law_number, ingested)
        search = SEARCH_LAW.get(law_number)
        sources.append(
            {
                "id": law_number,
                "label": law_number,
                "kind": meta["kind"],
                "status": "em_uso" if present else "nao_ingerido",
                "searchable": present,
                "search_law": search if present else None,
            }
        )
    tcu_present = any("tcu" in item.lower() for item in ingested)
    sources.append(
        {
            "id": "tcu",
            "label": "TCU",
            "kind": "jurisprudencia",
            "status": "quarentena" if tcu_present else "nao_ingerido",
            "searchable": False,
            "search_law": None,
        }
    )
    return sources
