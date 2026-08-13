"""
Geração de pontuação consolidada da análise (LLM + fallback determinístico).

Extraído do antigo engine.py: a pontuação é um estágio final do pipeline e
não pertence à orquestração.
"""

from app.services.analyzer.json_utils import parse_json_response
from app.services.analyzer.prompts import SCORING_PROMPT, SYSTEM_PROMPT


async def generate_scores(llm, corrections: list[dict], total_items: int) -> dict:
    """Gera pontuação consolidada via LLM."""
    # Resumir correções para o prompt
    summary_parts = []
    for i, c in enumerate(corrections[:50], 1):  # Limitar a 50 correções
        summary_parts.append(
            f"{i}. [{c.get('category', '?')}] [{c.get('severity', '?')}] "
            f"{c.get('problem', 'N/A')[:100]}"
        )

    corrections_summary = "\n".join(summary_parts) if summary_parts else "Nenhuma correção identificada."

    user_prompt = SCORING_PROMPT.format(
        corrections_summary=corrections_summary,
        total_items=total_items,
        total_corrections=len(corrections),
    )

    response = await llm.generate(SYSTEM_PROMPT, user_prompt)
    scores = parse_json_response(response)

    # Se retornou lista, pegar primeiro item
    if isinstance(scores, list) and scores:
        scores = scores[0]

    if not isinstance(scores, dict):
        raise ValueError("Resposta de pontuação não é um JSON válido.")

    return scores


def calculate_fallback_scores(corrections: list[dict], total_items: int) -> dict:
    """Pontuação determinística caso a LLM falhe na sumarização final."""
    cat_penalties = {"juridica": 0.0, "tecnica": 0.0, "redacao": 0.0, "estrutural": 0.0}
    has_critical = False
    has_high = False

    sev_weights = {"critico": 2.5, "alto": 1.5, "medio": 0.7, "baixo": 0.2}

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
        (score_juridical * 0.35 + score_technical * 0.30 + score_structural * 0.20 + score_writing * 0.15), 1
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
        f"Análise concluída com {len(corrections)} apontamento(s) de atenção formulados pelos 4 agentes especialistas. "
        f"Pontuação consolidada do Termo de Referência: {score_overall}/10. Nível de Risco Global: {risk_level.upper()}."
    )

    return {
        "score_overall": score_overall,
        "score_juridical": score_juridical,
        "score_technical": score_technical,
        "score_writing": score_writing,
        "score_structural": score_structural,
        "risk_level": risk_level,
        "final_opinion": final_opinion,
    }