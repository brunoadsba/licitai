"""
Testes do extrator determinístico de regras (RF02).
"""

from app.services.rules.extractor import extrair_valor


ITENS = [
    {
        "item_number": "4.3",
        "title": "Da Vigência",
        "content": "A vigência será de 90 dias, com garantia de execução.",
    },
    {
        "item_number": "6.1",
        "title": "Base Legal",
        "content": "Conforme o art. 5 da Lei 14.133/2021, o prazo será trinta dias.",
    },
]


def test_numero_inteiro_com_ancora():
    regra = {
        "id": "vigencia",
        "rotulo": "Vigência",
        "tipo": "numero_inteiro",
        "ancora": "vigência",
    }
    assert extrair_valor(regra, ITENS) == 90


def test_numero_inteiro_sem_ancora():
    regra = {
        "id": "prazo",
        "rotulo": "Prazo",
        "tipo": "numero_inteiro",
    }
    assert extrair_valor(regra, ITENS) == 90  # primeiro número do texto


def test_numero_extenso():
    regra = {
        "id": "prazo_extenso",
        "rotulo": "Prazo",
        "tipo": "numero_extenso",
        "ancora": "prazo",
    }
    assert extrair_valor(regra, ITENS) == 30


def test_booleano_presente():
    regra = {
        "id": "garantia",
        "rotulo": "Garantia",
        "tipo": "booleano",
        "palavras_chave": ["garantia"],
    }
    assert extrair_valor(regra, ITENS) is True


def test_booleano_ausente():
    regra = {
        "id": "seguro",
        "rotulo": "Seguro",
        "tipo": "booleano",
        "palavras_chave": ["seguro", "apólice"],
    }
    assert extrair_valor(regra, ITENS) is False


def test_legal_presente():
    regra = {
        "id": "lei",
        "rotulo": "Lei",
        "tipo": "legal",
        "regex": r"14\.133/2021",
    }
    assert extrair_valor(regra, ITENS) is True


def test_legal_ausente():
    regra = {
        "id": "lei",
        "rotulo": "Lei",
        "tipo": "legal",
        "regex": r"8\.666/1993",
    }
    assert extrair_valor(regra, ITENS) is False


def test_ancora_numerica_restringe_a_item():
    regra = {
        "id": "prazo",
        "rotulo": "Prazo",
        "tipo": "numero_inteiro",
        "ancora": "6.1",
    }
    # No item 6.1 o primeiro número é 5 (art. 5)
    assert extrair_valor(regra, ITENS) == 5


def test_ancora_inexistente_retorna_none():
    regra = {
        "id": "x",
        "rotulo": "X",
        "tipo": "numero_inteiro",
        "ancora": "não existe",
    }
    assert extrair_valor(regra, ITENS) is None


def test_data():
    itens = [
        {
            "item_number": "1",
            "title": "Prazo",
            "content": "Entrega até 15/12/2026, improrrogável.",
        }
    ]
    regra = {"id": "entrega", "rotulo": "Entrega", "tipo": "data", "ancora": "entrega"}
    assert extrair_valor(regra, itens) == "2026-12-15"


def test_data_inexistente_retorna_none():
    itens = [
        {
            "item_number": "1",
            "title": "Prazo",
            "content": "Entrega em até 30 dias.",
        }
    ]
    regra = {"id": "entrega", "rotulo": "Entrega", "tipo": "data", "ancora": "entrega"}
    assert extrair_valor(regra, itens) is None


def test_percentual():
    itens = [
        {
            "item_number": "1",
            "title": "Reajuste",
            "content": "Reajuste anual de 4,5% sobre o valor.",
        }
    ]
    regra = {"id": "reajuste", "rotulo": "Reajuste", "tipo": "percentual", "ancora": "reajuste"}
    assert extrair_valor(regra, itens) == 4.5


def test_monetario():
    itens = [
        {
            "item_number": "1",
            "title": "Valor",
            "content": "O valor estimado é de R$ 1.500,00.",
        }
    ]
    regra = {"id": "valor", "rotulo": "Valor", "tipo": "monetario", "ancora": "valor"}
    assert extrair_valor(regra, itens) == 1500.0
