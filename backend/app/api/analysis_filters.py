"""Filtros de correções (SEI, status, severidade) — extraído de `api/analysis.py`."""

from fastapi import HTTPException

SEI_APPLICABLE_STATUSES = frozenset({"aprovada", "ajustada"})

SEVERITY_RANK = {
    "info": 0,
    "baixo": 1,
    "medio": 2,
    "alto": 3,
    "critico": 4,
}


def _filter_corrections(
    corrections: list,
    *,
    for_sei: bool = False,
    review_statuses: set[str] | None = None,
    severity_min: str | None = None,
) -> list:
    if for_sei:
        allowed = SEI_APPLICABLE_STATUSES
        items = [c for c in corrections if getattr(c, "review_status", None) in allowed]
    elif review_statuses is not None:
        items = [
            c for c in corrections if getattr(c, "review_status", None) in review_statuses
        ]
    else:
        items = list(corrections)

    if severity_min:
        min_rank = SEVERITY_RANK.get(severity_min)
        if min_rank is None:
            raise HTTPException(
                status_code=422,
                detail="severity_min inválido. Use: info, baixo, medio, alto, critico.",
            )
        items = [
            c
            for c in items
            if SEVERITY_RANK.get(getattr(c, "severity", "") or "", -1) >= min_rank
        ]
    return items
