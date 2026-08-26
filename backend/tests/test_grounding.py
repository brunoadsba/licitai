from app.services.analyzer.grounding import (
    is_legal_basis_valid,
    is_original_text_grounded,
)


def test_grounding_original_text_exato():
    assert is_original_text_grounded("Prazo de 12 meses", "O prazo de 12 meses contados da assinatura.") is True


def test_grounding_original_text_normalizado():
    assert is_original_text_grounded("PRAZO   DE 12 MESES", "prazo de 12 meses") is True
    assert is_original_text_grounded("vigência", "VIGÊNCIA do contrato é de 12 meses") is True


def test_grounding_original_text_nao_encontrado():
    assert is_original_text_grounded("texto inventado", "conteúdo real sem esse trecho") is False
    assert is_original_text_grounded("", "conteúdo") is False
    assert is_original_text_grounded("   ", "conteúdo") is False


def test_legal_basis_valido():
    refs = {"lei 14.133/2021", "art. 6", "lei 13.303/2016"}
    assert is_legal_basis_valid("Lei 14.133/2021, art. 6º, XXIII", refs) is True
    assert is_legal_basis_valid("conforme Art. 6 da Lei 14.133/2021", refs) is True


def test_legal_basis_invalido():
    refs = {"lei 14.133/2021", "art. 6"}
    assert is_legal_basis_valid("Lei 9.999/2099 inventada", refs) is False


def test_legal_basis_none():
    assert is_legal_basis_valid(None, {"lei 14.133/2021"}) is None
    assert is_legal_basis_valid("", {"lei 14.133/2021"}) is None
    assert is_legal_basis_valid("Lei 14.133/2021", set()) is None
