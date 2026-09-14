"""
Testes do validador de respostas do Copiloto (T7).

Garantem o contrato de grounding: resposta factual exige citação válida ou
recusa explícita; `suggested_actions` do LLM são sempre descartadas;
source_id inexistente → fail-closed.
"""

import json

import pytest

from app.services.chat.validator import (
    REFUSAL_MESSAGE,
    ValidatedAnswer,
    _extract_json,
    normalize_reason,
    validate_llm_answer,
    warning_message_pt,
)
from app.services.chat.warnings_pt import FORA_ESCOPO_MESSAGE


def _resposta_ok(citations=True, suggested=(), source_id="legal:1"):
    dados = {
        "refused": False,
        "answer": "Resposta factual de teste.",
        "grounded": True,
        "confidence": 0.87,
        "citations": (
            [
                {
                    "type": "legal",
                    "source_id": source_id,
                    "reference": "Lei 14.133/2021, art. 5º",
                    "title": "Lei 14.133/2021",
                    "snippet": "A contratação observará...",
                }
            ]
            if citations
            else []
        ),
        "suggested_actions": list(suggested),
    }
    return json.dumps(dados, ensure_ascii=False)


class TestExtractJson:
    def test_json_puro(self):
        assert _extract_json('{"a": 1}') == {"a": 1}

    def test_json_com_fences_markdown(self):
        raw = '```json\n{"a": 1}\n```'
        assert _extract_json(raw) == {"a": 1}

    def test_json_com_ruido_ao_redor(self):
        raw = 'Texto antes {"a": 1} texto depois'
        assert _extract_json(raw) == {"a": 1}

    def test_json_invalido_levanta_erro(self):
        with pytest.raises(ValueError):
            _extract_json("não é json")


class TestValidateAnswer:
    def test_resposta_valida_com_citacao(self):
        resultado: ValidatedAnswer = validate_llm_answer(
            _resposta_ok(),
            require_grounding=True,
            valid_source_ids={"legal:1"},
        )
        assert not resultado.refused
        assert resultado.content == "Resposta factual de teste."
        assert resultado.grounded is True
        assert resultado.confidence == 0.87
        assert len(resultado.citations) == 1
        assert resultado.citations[0].reference == "Lei 14.133/2021, art. 5º"
        assert resultado.citations[0].source_id == "legal:1"

    def test_suggested_actions_sao_descartadas(self):
        resultado: ValidatedAnswer = validate_llm_answer(
            _resposta_ok(
                suggested=[{"action": "editar", "description": "mudar item"}]
            ),
            require_grounding=True,
            valid_source_ids={"legal:1"},
        )
        assert not hasattr(resultado, "suggested_actions")
        assert not resultado.refused

    def test_sem_citacao_com_grounding_obrigatorio_recusa(self):
        resultado: ValidatedAnswer = validate_llm_answer(
            _resposta_ok(citations=False),
            require_grounding=True,
            valid_source_ids={"legal:1"},
        )
        assert resultado.refused is True
        assert resultado.content == REFUSAL_MESSAGE
        assert resultado.reason == "sem-citacao"

    def test_sem_citacao_sem_grounding_obrigatorio_aceita(self):
        resultado: ValidatedAnswer = validate_llm_answer(
            _resposta_ok(citations=False),
            require_grounding=False,
            valid_source_ids=set(),
        )
        assert not resultado.refused
        assert resultado.content == "Resposta factual de teste."
        assert resultado.citations == []

    def test_source_id_inexistente_fail_closed(self):
        resultado = validate_llm_answer(
            _resposta_ok(source_id="legal:999"),
            require_grounding=True,
            valid_source_ids={"legal:1"},
        )
        assert resultado.refused is True
        assert resultado.reason == "source-id-inexistente"

    def test_recusa_explicita_do_llm(self):
        raw = json.dumps(
            {"refused": True, "reason": "sem-fontes", "answer": "não sei"}
        )
        resultado: ValidatedAnswer = validate_llm_answer(
            raw, require_grounding=True, valid_source_ids={"legal:1"}
        )
        assert resultado.refused is True
        assert resultado.reason == "sem-fontes"
        assert resultado.content == REFUSAL_MESSAGE
        assert "não sei" not in resultado.content
        assert warning_message_pt(resultado.reason) is None

    def test_recusa_reason_ingles_vira_fora_escopo_pt(self):
        english = (
            "The request does not pertain to public procurement, "
            "analysis of Terms of Reference, or the provided sources."
        )
        raw = json.dumps(
            {"refused": True, "reason": english, "answer": english},
            ensure_ascii=False,
        )
        resultado = validate_llm_answer(
            raw, require_grounding=True, valid_source_ids={"legal:1"}
        )
        assert resultado.refused is True
        assert resultado.reason == "fora-escopo"
        assert resultado.content == FORA_ESCOPO_MESSAGE
        assert "pertain" not in resultado.content.lower()
        assert "procurement" not in resultado.content.lower()
        warning = warning_message_pt(resultado.reason)
        assert warning is None or "pertain" not in warning.lower()

    def test_normalize_reason_slug_conhecido(self):
        assert normalize_reason("sem-citacao") == "sem-citacao"
        assert normalize_reason("FORA-ESCOPO") == "fora-escopo"

    def test_normalize_reason_prosa_desconhecida_vira_recusa_llm(self):
        assert normalize_reason("algum texto aleatório do modelo") == "recusa-llm"

    def test_resposta_nao_json_recusa(self):
        resultado: ValidatedAnswer = validate_llm_answer(
            "isso não é um json", require_grounding=True
        )
        assert resultado.refused is True
        assert resultado.reason == "resposta-invalida"

    def test_confiance_normalizada_entre_0_e_1(self):
        raw = json.dumps(
            {
                "refused": False,
                "answer": "ok",
                "grounded": True,
                "confidence": 2.5,
                "citations": [
                    {
                        "type": "legal",
                        "source_id": "legal:1",
                        "reference": "r",
                        "title": "t",
                        "snippet": "s",
                    }
                ],
            }
        )
        resultado: ValidatedAnswer = validate_llm_answer(
            raw, require_grounding=True, valid_source_ids={"legal:1"}
        )
        assert resultado.confidence == 1.0
