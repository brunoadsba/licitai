"""
Golden set — régua de confiabilidade (TP/FP/FN + checklist Art. 6º XXIII).

Preditor: FakeLLM determinístico (`fake_predict_findings`), não cópia de expected.
Meta: precision ≥ 0.88, recall ≥ 0.80, ≥10 fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.analyzer.fake_llm_golden import fake_predict_findings
from app.services.analyzer.grounding import (
    is_legal_basis_valid,
    is_original_text_grounded,
    make_legal_ref,
)
from app.services.analyzer.prompts import SYSTEM_PROMPT
from app.services.generator.validator import validate_tr_completeness
from app.services.legal.art6_xxiii import ART6_XXIII_ELEMENTS, art6_keys

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "e2e" / "golden"
PRECISION_THRESHOLD = 0.88
RECALL_THRESHOLD = 0.80
MIN_FIXTURES = 10


def _load_tr(name: str) -> dict:
    return json.loads((GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _finding_key(finding: dict) -> tuple[str, str]:
    return (
        (finding.get("original_text") or "").strip().lower(),
        (finding.get("category") or "").strip().lower(),
    )


def _score_findings(
    predicted: list[dict], expected: list[dict]
) -> tuple[int, int, int, float]:
    """Retorna (tp, fp, fn, precision)."""
    exp = {_finding_key(e) for e in expected if _finding_key(e)[0]}
    pred = {_finding_key(p) for p in predicted if _finding_key(p)[0]}
    tp = len(exp & pred)
    fp = len(pred - exp)
    fn = len(exp - pred)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    return tp, fp, fn, precision


def test_art6_checklist_alineas_a_j():
    """Checklist canônico = alíneas a–j; sem garantia/sanções/cronograma."""
    keys = art6_keys()
    alineas = [e.alinea for e in ART6_XXIII_ELEMENTS]
    assert keys == [
        "objeto",
        "fundamentacao",
        "descricao_solucao",
        "requisitos",
        "modelo_execucao",
        "modelo_gestao",
        "criterios_medicao_pagamento",
        "selecao_fornecedor",
        "estimativa_valor",
        "adequacao_orcamentaria",
    ]
    assert alineas == list("abcdefghij")
    forbidden = {"garantia", "infracoes_sancoes", "sancoes", "cronograma", "cronograma_fisico"}
    assert forbidden.isdisjoint(set(keys))
    prompt_lower = SYSTEM_PROMPT.lower()
    assert "garantia" in prompt_lower and "sanções" in prompt_lower and "cronograma" in prompt_lower
    assert "a–j" in SYSTEM_PROMPT or "a-j" in prompt_lower


def test_golden_checklist_completo():
    tr = _load_tr("tr_001")
    faltantes = validate_tr_completeness(tr["itens"])
    assert faltantes == [], f"tr_001 deveria estar completo, faltantes: {faltantes}"
    assert tr["expected_checklist"] == []


def test_golden_checklist_incompleto():
    tr = _load_tr("tr_002")
    faltantes = validate_tr_completeness(tr["itens"])
    expected = set(tr["expected_checklist"])
    assert set(faltantes) == expected
    assert expected.issubset(set(art6_keys()))


def test_golden_grounding_pairs():
    tr = _load_tr("tr_003")
    itens_text = "\n".join(f"{i['title']} {i['content']}" for i in tr["itens"])
    refs = {make_legal_ref("Lei 14.133/2021", "6")}
    for corr in tr["expected_correcoes"]:
        grounded = is_original_text_grounded(corr["original_text"], itens_text)
        assert grounded == corr["grounded"], f"grounding falhou para {corr['original_text'][:30]}"
        valid = is_legal_basis_valid(corr["legal_basis"], refs)
        if corr["grounded"]:
            assert valid is True
        else:
            assert valid is False


def test_golden_tp_fp_fn_precision_fakellm():
    """Precision/recall com FakeLLM determinístico (não copia expected)."""
    fixtures = sorted(GOLDEN_DIR.glob("tr_*.json"))
    assert len(fixtures) >= MIN_FIXTURES

    total_tp = total_fp = total_fn = 0
    saw_fp = False
    for path in fixtures:
        tr = json.loads(path.read_text(encoding="utf-8"))
        expected = tr.get("expected_findings") or []
        predicted = fake_predict_findings(tr)
        tp, fp, fn, _ = _score_findings(predicted, expected)
        if fp:
            saw_fp = True
        total_tp += tp
        total_fp += fp
        total_fn += fn

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 1.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 1.0
    assert precision >= PRECISION_THRESHOLD, (
        f"precision={precision:.2f} < {PRECISION_THRESHOLD} "
        f"(tp={total_tp} fp={total_fp} fn={total_fn})"
    )
    assert recall >= RECALL_THRESHOLD, (
        f"recall={recall:.2f} < {RECALL_THRESHOLD} (tp={total_tp} fn={total_fn})"
    )
    # tr_010 injeta FP deliberado — régua não é tautológica
    assert saw_fp, "esperava ao menos 1 FP (tr_010) para validar a régua"


def test_golden_adversarial_injection_nao_inventa_finding():
    tr = _load_tr("tr_009")
    assert tr.get("adversarial") is True
    predicted = fake_predict_findings(tr)
    blob = " ".join(p["original_text"].lower() for p in predicted)
    assert "garantia" not in blob
    assert "50%" not in blob
    assert predicted == []


def test_golden_fixtures_structure():
    fixtures = sorted(GOLDEN_DIR.glob("tr_*.json"))
    assert len(fixtures) >= MIN_FIXTURES, f"esperava ≥{MIN_FIXTURES}, achei {len(fixtures)}"
    required = {"id", "descricao", "itens"}
    for path in fixtures:
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = required - set(data)
        assert not missing, f"{path.name} sem campos: {missing}"
        assert isinstance(data["itens"], list) and data["itens"], f"{path.name} sem itens"
