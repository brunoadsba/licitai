from app.utils.pii_scrub import scrub


def test_scrub_email_cpf_token():
    s = scrub("contato joao@codeba.ba.gov.br cpf 123.456.789-09 Bearer abc123")
    assert "joao@codeba" not in s
    assert "123.456.789-09" not in s
    assert "abc123" not in s
    assert "[email]" in s and "[cpf]" in s


def test_scrub_empty_passthrough():
    assert scrub("") == ""
