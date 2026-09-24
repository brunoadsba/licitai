"""Métricas de recuperação e comparação de baseline (tolerância em p.p.)."""

from __future__ import annotations

import math


def recall_at_k(hits: list[bool], k: int) -> float:
    window = hits[:k]
    return 1.0 if any(window) else 0.0


def reciprocal_rank(hits: list[bool]) -> float:
    for i, hit in enumerate(hits):
        if hit:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(relevances: list[float], k: int) -> float:
    window = relevances[:k]
    dcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(window))
    ideal = sorted(window, reverse=True)
    idcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal))
    if idcg <= 0:
        return 0.0
    return dcg / idcg


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((p / 100) * (len(ordered) - 1))))
    return ordered[idx]


def regression_breaches(
    current: dict[str, float],
    baseline: dict[str, float],
    tolerance_pp: float,
) -> list[str]:
    """Falha se a métrica cair mais que `tolerance_pp` pontos percentuais."""
    breaches: list[str] = []
    delta = tolerance_pp / 100.0
    for key, base in baseline.items():
        now = current.get(key)
        if now is None:
            breaches.append(f"{key}: ausente no resultado atual")
            continue
        if now + 1e-9 < base - delta:
            breaches.append(
                f"{key}: {now:.3f} < baseline {base:.3f} - {tolerance_pp:.1f}pp"
            )
    return breaches
