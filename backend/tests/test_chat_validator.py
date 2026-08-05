"""
Testes do validador de respostas do Copiloto (T7).

Garantem o contrato de grounding: resposta factual exige citação válida ou
recusa explícita; `suggested_actions` do LLM são sempre descartadas.
"""

import json

import pytest

from app.services.chat.validator import (
    REFUSAL_MESSAGE,
    ValidatedAnswer,
    _extract_json,
    validate_llm_answer,
)


def _resposta_ok(citations=True, suggested=()):
    dados = {
        "refused": False,
        "answer": "Resposta factual de teste.",
        "grounded": True,
        "confidence": 0.87,
        "citations": (
            [
                {
                    "type": "legal",
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
            _resposta_ok(), require_grounding=True
        )
        assert not resultado.refused
        assert resultado.content == "Resposta factual de teste."
        assert resultado.grounded is True
        assert resultado.confidence == 0.87
        assert len(resultado.citations) == 1
        assert resultado.citations[0].reference == "Lei 14.133/2021, art. 5º"

    def test_suggested_actions_sao_descartadas(self):
        resultado: ValidatedAnswer = validate_llm_answer(
            _resposta_ok(
                suggested=[{"action": "editar", "description": "mudar item"}]
            ),
            require_grounding=True,
        )
        assert not hasattr(resultado, "suggested_actions")
        assert not resultado.refused

    def test_sem_citacao_com_grounding_obrigatorio_recusa(self):
        resultado: ValidatedAnswer = validate_llm_answer(
            _resposta_ok(citations=False), require_grounding=True
        )
        assert resultado.refused is True
        assert resultado.content == REFUSAL_MESSAGE
        assert resultado.reason == "sem-citacao"

    def test_sem_citacao_sem_grounding_obrigatorio_aceita(self):
        resultado: ValidatedAnswer = validate_llm_answer(
            _resposta_ok(citations=False), require_grounding=False
        )
        assert not resultado.refused
        assert resultado.content == "Resposta factual de teste."
        assert resultado.citations == []

    def test_recusa_explicita_do_llm(self):
        raw = json.dumps(
            {"refused": True, "reason": "sem-fontes", "answer": "não sei"}
        )
        resultado: ValidatedAnswer = validate_llm_answer(
            raw, require_grounding=True
        )
        assert resultado.refused is True
        assert resultado.reason == "sem-fontes"

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
                    {"type": "legal", "reference": "r", "title": "t", "snippet": "s"}
                ],
            }
        )
        resultado: ValidatedAnswer = validate_llm_answer(
            raw, require_grounding=True
        )
        assert resultado.confidence == 1.0
