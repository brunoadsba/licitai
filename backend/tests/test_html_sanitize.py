"""Fase 0C: HTML do SEI não executa script nem atributos perigosos."""

from app.services.analyzer.html_sanitize import sanitize_html


def test_remove_script_e_onerror():
    sujo = (
        '<p>ok</p><script>alert(1)</script>'
        '<img src=x onerror="alert(1)">'
        '<h2 onclick="steal()">título</h2>'
    )
    limpo = sanitize_html(sujo)
    assert "<script" not in limpo.lower()
    assert "onerror" not in limpo.lower()
    assert "onclick" not in limpo.lower()
    assert "<img" not in limpo.lower()
    assert "ok" in limpo
    assert "título" in limpo


def test_escapa_nome_de_arquivo_no_fluxo():
    sujo = '<h1>TR</h1><p><img src=x onerror=alert(1)></p>'
    limpo = sanitize_html(sujo)
    assert "onerror" not in limpo
    assert "<h1>TR</h1>" in limpo


def test_mantem_estrutura_do_tr():
    html = "<h1>TR</h1><h2>1.1 Objeto</h2><p>texto<br>linha</p>"
    limpo = sanitize_html(html)
    assert "<h1>TR</h1>" in limpo
    assert "<h2>1.1 Objeto</h2>" in limpo
    assert "<br>" in limpo
