"""
Geração de pontuação consolidada da análise.

Primário: scoring determinístico (counts/severidade) + invariantes de risco.
Secundário: opinião textual via LLM (não sobrescreve notas numéricas).
"""

from __future__ import annotations

import logging

from app.services.analyzer.json_utils import parse_json_response
from app.services.analyzer.prompts import SCORING_PROMPT, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

VALID_RISK_LEVELS = {"baixo", "medio", "alto", "critico"}
_SCORE_KEYS = (
    "score_overall",
    "score_juridical",
    "score_technical",
    "score_writing",
    "score_structural",
)

# Ordem de gravidade para invariantes (maior = pior)
_RISK_RANK = {"baixo": 0, "medio": 1, "alto": 2, "critico": 3}


def sanitize_scores(scores: dict) -> dict:
    """Valida e normaliza as notas vindas do LLM antes de persistir.

    Regras:
    - Cada nota deve ser numérica (bool não conta) e é clampada a [0, 10],
      arredondada para 1 casa decimal.
    - Qualquer nota ausente ou não numérica levanta ValueError — o chamador
      (engine) trata isso aplicando o cálculo determinístico de fallback.
    - risk_level inválido é substituído por "medio" (default histórico).
    """
    sanitized: dict = {}
    for key in _SCORE_KEYS:
        value = scores.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Nota '{key}' inválida vinda do LLM: {value!r}")
        sanitized[key] = round(max(0.0, min(10.0, float(value))), 1)

    risk_level = scores.get("risk_level")
    if isinstance(risk_level, str) and risk_level.strip().lower() in VALID_RISK_LEVELS:
        sanitized["risk_level"] = risk_level.strip().lower()
    else:
        sanitized["risk_level"] = "medio"

    opinion = scores.get("final_opinion", "")
    sanitized["final_opinion"] = opinion if isinstance(opinion, str) else ""

    return sanitized


def apply_risk_invariants(scores: dict, corrections: list[dict]) -> dict:
    """Garante coerência risco ↔ severidade das correções.

    - Se existe correção critica → risk_level >= critico
    - Se existe alto (sem critico) → risk_level >= alto
    - risk_level nunca é mais brando que o derivado das notas
    """
    out = dict(scores)
    has_critical = any(c.get("severity") == "critico" for c in corrections)
    has_high = any(c.get("severity") == "alto" for c in corrections)

    derived = out.get("risk_level", "medio")
    if derived not in VALID_RISK_LEVELS:
        derived = "medio"

    floor = "baixo"
    if has_critical:
        floor = "critico"
    elif has_high:
        floor = "alto"

    if _RISK_RANK[derived] < _RISK_RANK[floor]:
        out["risk_level"] = floor
    else:
        out["risk_level"] = derived

    overall = float(out.get("score_overall") or 0)
    if overall < 5.0 and _RISK_RANK[out["risk_level"]] < _RISK_RANK["critico"]:
        out["risk_level"] = "critico"
    elif overall < 7.0 and _RISK_RANK[out["risk_level"]] < _RISK_RANK["alto"]:
        out["risk_level"] = "alto"

    return out


def calculate_deterministic_scores(corrections: list[dict], total_items: int) -> dict:
    """Pontuação primária derivada de counts/severidade (sem LLM)."""
    cat_penalties = {"juridica": 0.0, "tecnica": 0.0, "redacao": 0.0, "estrutural": 0.0}
    has_critical = False
    has_high = False

    sev_weights = {"critico": 2.5, "alto": 1.5, "medio": 0.7, "baixo": 0.2, "info": 0.1}

    for c in corrections:
        cat = c.get("category", "tecnica")
        sev = c.get("severity", "medio")
        weight = sev_weights.get(sev, 0.7)
        if cat in cat_penalties:
            cat_penalties[cat] += weight
        if sev == "critico":
            has_critical = True
        elif sev == "alto":
            has_high = True

    score_juridical = round(max(0.0, min(10.0, 10.0 - cat_penalties["juridica"])), 1)
    score_technical = round(max(0.0, min(10.0, 10.0 - cat_penalties["tecnica"])), 1)
    score_writing = round(max(0.0, min(10.0, 10.0 - cat_penalties["redacao"])), 1)
    score_structural = round(max(0.0, min(10.0, 10.0 - cat_penalties["estrutural"])), 1)

    score_overall = round(
        (
            score_juridical * 0.35
            + score_technical * 0.30
            + score_structural * 0.20
            + score_writing * 0.15
        ),
        1,
    )

    if has_critical or score_overall < 5.0:
        risk_level = "critico"
    elif has_high or score_overall < 7.0:
        risk_level = "alto"
    elif score_overall < 8.5:
        risk_level = "medio"
    else:
        risk_level = "baixo"

    final_opinion = (
        f"Análise concluída com {len(corrections)} apontamento(s) "
        f"em {total_items} item(ns). "
        f"Pontuação consolidada: {score_overall}/10. "
        f"Nível de risco: {risk_level.upper()}."
    )

    scores = {
        "score_overall": score_overall,
        "score_juridical": score_juridical,
        "score_technical": score_technical,
        "score_writing": score_writing,
        "score_structural": score_structural,
        "risk_level": risk_level,
        "final_opinion": final_opinion,
    }
    return apply_risk_invariants(scores, corrections)


# Alias histórico
def calculate_fallback_scores(corrections: list[dict], total_items: int) -> dict:
    return calculate_deterministic_scores(corrections, total_items)


async def generate_scores(llm, corrections: list[dict], total_items: int) -> dict:
    """
    Scoring determinístico primário + opinião LLM secundária.

    Notas numéricas e risk_level vêm do cálculo determinístico.
    O LLM só enriquece `final_opinion` quando disponível.
    """
    scores = calculate_deterministic_scores(corrections, total_items)

    summary_parts = []
    for i, c in enumerate(corrections[:50], 1):
        summary_parts.append(
            f"{i}. [{c.get('category', '?')}] [{c.get('severity', '?')}] "
            f"{c.get('problem', 'N/A')[:100]}"
        )
    corrections_summary = (
        "\n".join(summary_parts) if summary_parts else "Nenhuma correção identificada."
    )
    user_prompt = SCORING_PROMPT.format(
        corrections_summary=corrections_summary,
        total_items=total_items,
        total_corrections=len(corrections),
    )

    try:
        response = await llm.generate(SYSTEM_PROMPT, user_prompt)
        llm_scores = parse_json_response(response)
        if isinstance(llm_scores, list) and llm_scores:
            llm_scores = llm_scores[0]
        if isinstance(llm_scores, dict):
            # Só adota opinião se o payload LLM for coerente (notas válidas).
            try:
                sanitized = sanitize_scores(llm_scores)
                if sanitized.get("final_opinion"):
                    scores["final_opinion"] = sanitized["final_opinion"]
            except ValueError:
                logger.info(
                    "Payload LLM de scoring inválido; mantendo opinião determinística"
                )
    except Exception:
        logger.warning(
            "Opinião LLM indisponível; mantendo final_opinion determinístico",
            exc_info=True,
        )

    return apply_risk_invariants(scores, corrections)
