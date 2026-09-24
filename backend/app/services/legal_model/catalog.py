"""Classificação estável das normas conhecidas do piloto."""

from __future__ import annotations

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
