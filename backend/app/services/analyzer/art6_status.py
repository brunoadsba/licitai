"""Checklist Art. 6º XXIII a partir dos itens parseados + findings de ausência."""

from __future__ import annotations

from app.services.generator.validator import ART6_COVERAGE_TARGET, validate_tr_completeness
from app.services.legal.art6_xxiii import ART6_XXIII_ELEMENTS


def build_art6_checklist(
    items: list,
    corrections: list | None = None,
) -> list[dict]:
    """
    Retorna lista de dicts {key, alinea, label, status}.
    missing = keyword ausente no TR; uncertain = há finding estrutural de ausência.
    """
    secoes = [
        {
            "item_number": getattr(i, "item_number", "") or "",
            "title": getattr(i, "title", "") or "",
            "content": getattr(i, "content", "") or "",
        }
        for i in (items or [])
    ]
    faltantes = set(validate_tr_completeness(secoes))

    uncertain: set[str] = set()
    for c in corrections or []:
        if getattr(c, "category", None) != "estrutural":
            continue
        situation = (getattr(c, "situation", "") or "").lower()
        problem = (getattr(c, "problem", "") or "").lower()
        blob = f"{situation} {problem}"
        for elem in ART6_XXIII_ELEMENTS:
            if elem.key in blob or f"ausencia:{elem.key}" in blob or elem.alinea in blob:
                uncertain.add(elem.key)

    out: list[dict] = []
    for elem in ART6_XXIII_ELEMENTS:
        if elem.key in uncertain and elem.key in faltantes:
            status = "uncertain"
        elif elem.key in faltantes:
            status = "missing"
        else:
            status = "present"
        out.append(
            {
                "key": elem.key,
                "alinea": elem.alinea,
                "label": elem.title,
                "status": status,
            }
        )
    return out


def summarize_art6_coverage(checklist: list[dict], target: float = ART6_COVERAGE_TARGET) -> dict:
    """Métrica explícita rumo a ≥90% de alíneas a–j presentes."""
    total = len(checklist) or len(ART6_XXIII_ELEMENTS)
    present = sum(1 for row in checklist if row.get("status") == "present")
    coverage = round(present / total, 3) if total else 0.0
    return {
        "art6_present": present,
        "art6_total": total,
        "art6_coverage": coverage,
        "art6_meets_target": coverage >= target,
    }
