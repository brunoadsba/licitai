"""Fase 4 — recalibragem pós-review + precision visível.

Aceite: risco cai após rejeição em massa; precision = (aprovadas+ajustadas)/revisadas.
"""

from app.services.analyzer.scoring import calculate_deterministic_scores


def _corr(sev="alto", cat="juridica"):
    return {"category": cat, "severity": sev, "problem": "x"}


def precision(aprovadas: int, ajustadas: int, rejeitadas: int) -> float:
    revisadas = aprovadas + ajustadas + rejeitadas
    if not revisadas:
        return 1.0
    return (aprovadas + ajustadas) / revisadas


def test_risco_cai_apos_rejeicao_em_massa():
    # 11 achados, 9 alto/critico -> risco alto/critico
    antes = calculate_deterministic_scores([_corr("alto")] * 9 + [_corr("medio")] * 2, 10)
    assert antes["risk_level"] in ("alto", "critico")
    # Após 9 rejeitadas, restam 2 medios -> risco cai
    depois = calculate_deterministic_scores([_corr("medio")] * 2, 10)
    assert depois["risk_level"] in ("baixo", "medio")
    assert depois["score_overall"] > antes["score_overall"]


def test_precision_afd39876():
    # 1 aprovada + 1 ajustada em 11 -> 0.18
    assert abs(precision(1, 1, 9) - 0.18) < 0.01
    # Meta Fase 4
    assert precision(9, 0, 1) >= 0.80
