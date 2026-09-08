from app.services.analyzer.grounding import (
    article_token_matches,
    is_legal_basis_valid,
    is_original_text_grounded,
    make_legal_ref,
    should_fail_closed_legal,
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


def test_legal_basis_valido_par():
    refs = {make_legal_ref("Lei 14.133/2021", "6")}
    assert is_legal_basis_valid("Lei 14.133/2021, art. 6º, XXIII", refs) is True
    assert is_legal_basis_valid("conforme Art. 6 da Lei 14.133/2021", refs) is True


def test_legal_basis_art6_nao_casa_art67():
    """Boundary: Art. 6 não deve validar Art. 67."""
    refs = {make_legal_ref("14.133/2021", "6")}
    assert is_legal_basis_valid("Art. 67 da Lei 14.133/2021", refs) is False
    assert article_token_matches("6", "Art. 67 da Lei 14.133/2021") is False
    assert article_token_matches("67", "Art. 67 da Lei 14.133/2021") is True


def test_legal_basis_legado_flat_com_boundary():
    refs = {"lei 14.133/2021", "art. 6"}
    assert is_legal_basis_valid("Lei 14.133/2021, art. 6º, XXIII", refs) is True
    assert is_legal_basis_valid("Art. 67 da Lei 14.133/2021", refs) is False


def test_legal_basis_invalido():
    refs = {make_legal_ref("14.133/2021", "6")}
    assert is_legal_basis_valid("Lei 9.999/2099 inventada, art. 1", refs) is False


def test_legal_basis_none():
    assert is_legal_basis_valid(None, {make_legal_ref("14.133/2021", "6")}) is None
    assert is_legal_basis_valid("", {make_legal_ref("14.133/2021", "6")}) is None
    assert is_legal_basis_valid("Lei 14.133/2021, art. 6", set()) is None


def test_fail_closed_alta_critica():
    assert should_fail_closed_legal(False, severity="alto") is True
    assert should_fail_closed_legal(False, importance="critica") is True
    assert should_fail_closed_legal(False, severity="medio") is False
    assert should_fail_closed_legal(True, severity="critico") is False
    assert should_fail_closed_legal(None, severity="alto") is False
