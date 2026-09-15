"""
Checagens determinísticas do revisor-assistente (puras, sem LLM).

Reaproveita exatamente as mesmas validações do `analysis_persistence`:
grounding do original_text, legal_basis no corpus, placeholders e
fail-closed para severidade alta/crítica. Zero alucinação local.
"""

from __future__ import annotations

import re

from app.services.analyzer.grounding import (
    is_legal_basis_valid,
    is_original_text_grounded,
    should_fail_closed_legal,
)
from app.services.reviewer.schemas import ReviewSuggestion

_PLACEHOLDER_RE = re.compile(
    r"\b[XYZ]\b|\[inserir[^\]]*\]|\[preencher[^\]]*\]|___+|\{[^}]+\}|a preencher|campo a preencher",
    re.IGNORECASE,
)


def has_placeholder(text: str | None) -> bool:
    if not text:
        return False
    return bool(_PLACEHOLDER_RE.search(text))


def suggest_for_correction(
    correction,
    *,
    item_content: str | None,
    valid_refs: set[str],
) -> ReviewSuggestion:
    """
    Sugestão determinística para uma correção (sem IO, sem LLM).

    Retorna {suggestion, confidence, reason, evidence}.
    Humano decide; IA só sugere (fail-closed).
    """
    cid = str(getattr(correction, "id", ""))
    original = getattr(correction, "original_text", "") or ""
    suggested = getattr(correction, "suggested_text", "") or ""
    legal_basis = getattr(correction, "legal_basis", None)
    severity = (getattr(correction, "severity", "") or "").lower()
    importance = (getattr(correction, "importance", "") or "").lower()
    category = (getattr(correction, "category", "") or "").lower()

    grounded = is_original_text_grounded(original, item_content or "")
    legal_valid = is_legal_basis_valid(legal_basis, valid_refs)
    placeholder = has_placeholder(suggested)
    fail_closed = should_fail_closed_legal(
        legal_valid, severity=severity, importance=importance
    )

    # Regras em ordem de prioridade (fail-closed/grounding primeiro).
    if not grounded and original.strip():
        return ReviewSuggestion(
            correction_id=cid,
            suggestion="rejeitar",
            confidence=0.95,
            reason="original_text não encontrado no item (possível alucinação)",
            evidence={"grounded": False, "legal_valid": legal_valid},
            grounded=False,
            legal_valid=legal_valid,
            has_placeholder=placeholder,
            fail_closed=False,
        )

    if fail_closed:
        return ReviewSuggestion(
            correction_id=cid,
            suggestion="rejeitar",
            confidence=0.90,
            reason="legal_basis inválido no corpus (fail-closed para severidade alta/crítica)",
            evidence={"grounded": grounded, "legal_valid": False},
            grounded=grounded,
            legal_valid=False,
            has_placeholder=placeholder,
            fail_closed=True,
        )

    if placeholder:
        return ReviewSuggestion(
            correction_id=cid,
            suggestion="ajustar",
            confidence=0.88,
            reason="texto sugerido com campos a preencher — ajustar antes de aprovar",
            evidence={"grounded": grounded, "legal_valid": legal_valid},
            grounded=grounded,
            legal_valid=legal_valid,
            has_placeholder=True,
            fail_closed=False,
        )

    # Coerência critico deve ser jurídica
    if severity == "critico" and category != "juridica":
        return ReviewSuggestion(
            correction_id=cid,
            suggestion="ajustar",
            confidence=0.62,
            reason="severidade crítica fora da categoria jurídica — revisar categoria/severidade",
            evidence={"grounded": grounded, "legal_valid": legal_valid},
            grounded=grounded,
            legal_valid=legal_valid,
            has_placeholder=False,
            fail_closed=False,
        )

    # Caso feliz: tudo válido
    if grounded and legal_valid is True:
        return ReviewSuggestion(
            correction_id=cid,
            suggestion="aprovar",
            confidence=0.84,
            reason="grounding OK e fundamento válido no corpus",
            evidence={"grounded": True, "legal_valid": True},
            grounded=True,
            legal_valid=True,
            has_placeholder=False,
            fail_closed=False,
        )

    if grounded and legal_valid is None:
        return ReviewSuggestion(
            correction_id=cid,
            suggestion="aprovar",
            confidence=0.68,
            reason="grounding OK; sem fundamento verificável no corpus (conferir manualmente)",
            evidence={"grounded": True, "legal_valid": None},
            grounded=True,
            legal_valid=None,
            has_placeholder=False,
            fail_closed=False,
        )

    # Fallback genérico
    return ReviewSuggestion(
        correction_id=cid,
        suggestion="aprovar",
        confidence=0.60,
        reason="sem bloqueios determinísticos — conferir fundamentação antes de aprovar",
        evidence={"grounded": grounded, "legal_valid": legal_valid},
        grounded=grounded,
        legal_valid=legal_valid,
        has_placeholder=placeholder,
        fail_closed=False,
    )
