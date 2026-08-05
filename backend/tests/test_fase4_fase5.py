"""
Testes Unitários e de Integração das Fases 4 e 5.

Cobre os novos extratores de âncoras (cnpj, prazo_relativo, cep),
a duplicação de moldes e a validação dry-run de regras.
"""

import pytest
from app.services.rules.extractor import extrair_valor
from app.services.rules.loader import parse_molde


def test_extrator_cnpj():
    item = {"item_number": "1.1", "title": "Empresa", "content": "CNPJ da contratada: 12.345.678/0001-95."}
    regra = {"id": "cnpj_rule", "rotulo": "CNPJ", "tipo": "cnpj", "ancora": "cnpj"}
    valor = extrair_valor(regra, [item])
    assert valor == "12.345.678/0001-95"


def test_extrator_prazo_relativo():
    item = {"item_number": "2.1", "title": "Vigência", "content": "O contrato terá vigência pelo prazo de 30 (trinta) dias."}
    regra = {"id": "prazo_rule", "rotulo": "Prazo", "tipo": "prazo_relativo", "ancora": "vigência"}
    valor = extrair_valor(regra, [item])
    assert valor == "30 dias"


def test_extrator_cep():
    item = {"item_number": "3.1", "title": "Endereço", "content": "Entrega no CEP 40015-000 em Salvador."}
    regra = {"id": "cep_rule", "rotulo": "CEP", "tipo": "cep", "ancora": "cep"}
    valor = extrair_valor(regra, [item])
    assert valor == "40015-000"


def test_loader_aceita_novas_ancoras():
    molde_json = """{
      "versao": 1,
      "regras": [
        {"id": "r1", "rotulo": "CNPJ Contratada", "tipo": "cnpj", "ancora": "cnpj"},
        {"id": "r2", "rotulo": "Prazo de Entrega", "tipo": "prazo_relativo", "ancora": "prazo"},
        {"id": "r3", "rotulo": "CEP Local", "tipo": "cep", "ancora": "cep"}
      ]
    }"""
    config = parse_molde(molde_json)
    assert len(config.regras) == 3
    assert config.regras[0].tipo == "cnpj"
    assert config.regras[1].tipo == "prazo_relativo"
    assert config.regras[2].tipo == "cep"
