"""Resposta do Copiloto sem UUID, source_id nem falha de agente."""

from types import SimpleNamespace

from app.services.chat.answer_sanitize import sanitize_answer, strip_parecer_audit
from app.services.chat.prompts import SYSTEM_PROMPT
from app.services.chat.sources import _is_operational_correction
from app.services.chat.validator import validate_llm_answer


def test_sanitize_remove_uuid_source_id_e_falha_agente():
    raw = (
        "O item falhou estrutural:failed "
        "correction:a1b2c3d4-e5f6-7890-abcd-ef1234567890 "
        "veja legal:abc."
    )
    cleaned = sanitize_answer(raw)
    assert "estrutural:failed" not in cleaned
    assert "correction:" not in cleaned
    assert "a1b2c3d4-e5f6-7890-abcd-ef1234567890" not in cleaned
    assert "legal:" not in cleaned


def test_strip_parecer_corta_rastro():
    texto = (
        "O TR está regular no objeto.\n"
        "Rastro das correções:\n"
        "- a1b2c3d4 · Art. 6 · DE: —\n"
        "Fontes do parecer: correções a1b2c3d4-e5f6-7890-abcd-ef1234567890.\n"
    )
    assert "Rastro" not in strip_parecer_audit(texto)
    assert "O TR está regular no objeto." in strip_parecer_audit(texto)


def test_validator_sanitiza_answer():
    raw = (
        '{"refused": false, "answer": "Prazo ok. estrutural:failed '
        'id 11111111-1111-1111-1111-111111111111", "grounded": true, '
        '"citations": [{"type": "legal", "source_id": "legal:1"}]}'
    )
    resultado = validate_llm_answer(
        raw, require_grounding=True, valid_source_ids={"legal:1"}
    )
    assert not resultado.refused
    assert "estrutural:failed" not in resultado.content
    assert "11111111-1111-1111-1111-111111111111" not in resultado.content


def test_prompt_guia_proibe_ruido():
    texto = SYSTEM_PROMPT.lower()
    assert "o que fazer agora" in texto
    assert "estrutural:failed" in texto
    assert "source_id" in texto


def test_correcao_operacional_nao_vira_fonte():
    ruim = SimpleNamespace(
        problem="Um ou mais agentes falharam: estrutural:failed",
        suggested_text="Reexecutar a análise deste item.",
        evidence={"coverage_errors": ["estrutural:failed"]},
    )
    boa = SimpleNamespace(
        problem="Prazo vago no objeto",
        suggested_text="Detalhar a vigência no item 1.4",
        evidence={},
    )
    assert _is_operational_correction(ruim) is True
    assert _is_operational_correction(boa) is False
