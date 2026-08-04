"""
Testes do loader de moldes de regras (RF02).
"""

import json

import pytest
from pydantic import ValidationError

from app.services.rules.loader import parse_molde


def molde_valido():
    return {
        "versao": 1,
        "regras": [
            {
                "id": "vigencia_dias",
                "rotulo": "Vigência mínima",
                "tipo": "numero_inteiro",
                "ancora": "vigência",
                "expectativa": 90,
            }
        ],
    }


def test_parse_molde_valido():
    molde = parse_molde(json.dumps(molde_valido()))
    assert len(molde.regras) == 1
    assert molde.regras[0].id == "vigencia_dias"
    assert molde.regras[0].tipo == "numero_inteiro"


def test_parse_json_invalido_levanta_validationerror():
    with pytest.raises(ValidationError):
        parse_molde("{{nao é json")


def test_tipo_invalido_levanta_validationerror():
    config = molde_valido()
    config["regras"][0]["tipo"] = "tipo_inexistente"
    with pytest.raises(ValidationError):
        parse_molde(json.dumps(config))


def test_ids_duplicados_levanta_validationerror():
    config = molde_valido()
    config["regras"].append(config["regras"][0])
    with pytest.raises(ValidationError):
        parse_molde(json.dumps(config))


def test_sem_regras_levanta_validationerror():
    config = {"versao": 1, "regras": []}
    with pytest.raises(ValidationError):
        parse_molde(json.dumps(config))


def test_aceita_todos_os_tipos():
    config = {
        "versao": 1,
        "regras": [
            {"id": "r1", "rotulo": "R1", "tipo": "numero_inteiro"},
            {"id": "r2", "rotulo": "R2", "tipo": "numero_extenso"},
            {"id": "r3", "rotulo": "R3", "tipo": "booleano",
             "palavras_chave": ["garantia"]},
            {"id": "r4", "rotulo": "R4", "tipo": "legal",
             "regex": r"14\.133/2021"},
            {"id": "r5", "rotulo": "R5", "tipo": "data"},
            {"id": "r6", "rotulo": "R6", "tipo": "percentual"},
            {"id": "r7", "rotulo": "R7", "tipo": "monetario"},
        ],
    }
    molde = parse_molde(json.dumps(config))
    assert {r.tipo for r in molde.regras} == {
        "numero_inteiro", "numero_extenso", "booleano", "legal",
        "data", "percentual", "monetario",
    }
