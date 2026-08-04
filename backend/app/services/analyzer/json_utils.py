"""
Utilitários de parsing e validação de respostas JSON do LLM.

O LLM pode responder com texto extra ao redor do JSON; estas funções
extraem e normalizam a estrutura esperada de correções e pontuações.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

# Valores válidos para campos de correção
VALID_CATEGORIES = {"juridica", "tecnica", "redacao", "estrutural"}
VALID_SEVERITIES = {"info", "baixo", "medio", "alto", "critico"}
VALID_IMPORTANCES = {"baixa", "media", "alta", "critica"}


def parse_json_response(response: str) -> list[dict] | dict:
    """
    Extrai e parseia JSON da resposta do LLM.
    Lida com respostas que podem conter texto extra.
    """
    # Tentar parsear diretamente
    try:
        parsed = json.loads(response)
        return parsed
    except json.JSONDecodeError:
        pass

    # Tentar extrair JSON de blocos de código
    json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", response)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Tentar encontrar array ou object JSON no texto
    for pattern in [r"\[[\s\S]*\]", r"\{[\s\S]*\}"]:
        match = re.search(pattern, response)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue

    logger.warning("Não foi possível parsear JSON da resposta do LLM")
    return []


def validate_correction(correction: dict) -> bool:
    """Valida se uma correção tem os campos obrigatórios."""
    required = ["category", "problem", "original_text", "suggested_text"]
    return all(correction.get(field) for field in required)


def sanitize_correction(correction: dict) -> dict:
    """Limpa e normaliza valores de uma correção."""
    category = correction.get("category", "tecnica").lower()
    if category not in VALID_CATEGORIES:
        category = "tecnica"

    severity = correction.get("severity", "medio").lower()
    if severity not in VALID_SEVERITIES:
        severity = "medio"

    importance = correction.get("importance", "media").lower()
    if importance not in VALID_IMPORTANCES:
        importance = "media"

    return {
        "category": category,
        "severity": severity,
        "situation": str(correction.get("situation", ""))[:2000],
        "problem": str(correction.get("problem", ""))[:2000],
        "risk": str(correction.get("risk", ""))[:2000],
        "original_text": str(correction.get("original_text", ""))[:5000],
        "suggested_text": str(correction.get("suggested_text", ""))[:5000],
        "justification": str(correction.get("justification", ""))[:2000],
        "legal_basis": str(correction.get("legal_basis", ""))[:500] or None,
        "importance": importance,
    }
