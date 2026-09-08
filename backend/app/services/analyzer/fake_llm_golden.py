"""
FakeLLM determinístico para o golden set.

Deriva findings a partir do texto dos itens + gaps do checklist Art. 6º XXIII.
Não copia `expected_findings` — TP/FP/FN medem a régua real.
"""

from __future__ import annotations

import re
import unicodedata

from app.services.generator.validator import validate_tr_completeness


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower()).strip()


def fake_predict_findings(tr: dict) -> list[dict]:
    """
    Preditor FakeLLM baseado em regras.

    - Gaps de checklist → findings estruturais `ausencia:<key>`
    - Heurísticas de texto (marca exclusiva, prazo ambíguo, vigilância)
    - FP intencional: se o id for tr_010, emite finding espúrio para medir FP
    """
    itens = tr.get("itens") or []
    blob = _norm(" ".join(f"{i.get('title', '')} {i.get('content', '')}" for i in itens))
    findings: list[dict] = []

    for key in validate_tr_completeness(itens):
        findings.append({"original_text": f"ausencia:{key}", "category": "estrutural"})

    if "marca exclusiva" in blob:
        # Normaliza para o rótulo anotado no golden
        findings.append({"original_text": "marca exclusiva XYZ", "category": "juridica"})

    if "prazo razoavel" in blob or "prazo a criterio" in blob:
        findings.append({"original_text": "prazo razoável", "category": "tecnica"})

    if "vigilancia armada" in blob:
        findings.append({"original_text": "vigilância armada", "category": "juridica"})

    if "direcionamento" in blob and "edital" in blob:
        findings.append({"original_text": "direcionamento no edital", "category": "juridica"})

    # FP deliberado (fixture tr_010) — preditor inventa finding inexistente
    if tr.get("id") == "tr_010":
        findings.append(
            {
                "original_text": "clausula fantasma inexistente",
                "category": "juridica",
            }
        )

    # Dedup por (texto, categoria)
    seen: set[tuple[str, str]] = set()
    unique: list[dict] = []
    for f in findings:
        key = (f["original_text"].strip().lower(), f["category"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)
    return unique
