"""Harness offline do recall: sem LLM, só compara o que já está no banco."""

from app.services.analyzer.recall_eval import evaluate_golden


def test_recall_conta_hits():
    expected = [
        {"item_number": "3.1.1", "keyword": "truncado"},
        {"item_number": "3.1.2", "keyword": "incompleto"},
        {"item_number": "3.1.4", "keyword": "abruptamente"},
    ]
    corrections = [
        {"problem": "título truncado no item", "situation": "", "original_text": "",
         "suggested_text": "", "justification": "", "risk": ""},
    ]
    out = evaluate_golden(expected, corrections)
    assert out["recall"] == 1 / 3
    assert out["hits"] == 1
    assert out["total"] == 3


def test_fp_conhecido_dispara_tripwire():
    out = evaluate_golden(
        [],
        [{"problem": "Um ou mais agentes falharam na análise", "situation": "",
          "original_text": "", "suggested_text": "", "justification": "", "risk": ""}],
        known_fps=[{"keyword": "Um ou mais agentes falharam"}],
    )
    assert out["fp_hits"] == 1
    assert out["recall"] == 1.0


def test_vazio_honesto():
    out = evaluate_golden([], [])
    assert out == {"recall": 1.0, "hits": 0, "total": 0,
                   "fp_hits": 0, "fp_total": 0, "fp_matched": []}
