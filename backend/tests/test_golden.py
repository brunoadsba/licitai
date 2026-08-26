import json
from pathlib import Path

from app.services.analyzer.grounding import is_legal_basis_valid, is_original_text_grounded
from app.services.generator.validator import validate_tr_completeness

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "e2e" / "golden"


def _load_tr(name: str) -> dict:
    return json.loads((GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8"))


def test_golden_checklist_completo():
    tr = _load_tr("tr_001")
    faltantes = validate_tr_completeness(tr["itens"])
    assert faltantes == [], f"tr_001 deveria estar completo, faltantes: {faltantes}"


def test_golden_checklist_incompleto():
    tr = _load_tr("tr_002")
    faltantes = validate_tr_completeness(tr["itens"])
    expected = set(tr["expected_checklist"])
    assert set(faltantes) == expected


def test_golden_grounding():
    tr = _load_tr("tr_003")
    itens_text = "\n".join(f"{i['title']} {i['content']}" for i in tr["itens"])
    refs = {"lei 14.133/2021", "art. 6"}
    for corr in tr["expected_correcoes"]:
        grounded = is_original_text_grounded(corr["original_text"], itens_text)
        assert grounded == corr["grounded"], f"grounding falhou para {corr['original_text'][:30]}"
        if corr["grounded"]:
            valid = is_legal_basis_valid(corr["legal_basis"], refs)
            assert valid is True
        else:
            valid = is_legal_basis_valid(corr["legal_basis"], refs)
            assert valid is False


def test_golden_precision_threshold():
    total = 0
    corretas = 0
    for name in ["tr_001", "tr_002", "tr_003"]:
        tr = _load_tr(name)
        faltantes = validate_tr_completeness(tr["itens"])
        if name == "tr_001":
            if not faltantes:
                corretas += 1
            total += 1
        if name == "tr_002":
            if set(faltantes) == set(tr["expected_checklist"]):
                corretas += 1
            total += 1
    assert corretas / total >= 0.88
