"""Tachado, (VETADO) e redação dada não misturam histórico com vigente."""

from app.services.parser.legal_marks import normalize_legal_text
from app.services.rag.loader import parse_law_text


FIXTURE = (
    "Art. 1º Texto vigente ~~revogado~~ permanece.\n"
    "Art. 2º (VETADO)\n"
    "Art. 3º Nova regra (Redação dada pela Lei 14.133/2021).\n"
)


def test_tachado_vira_historico():
    normalized = normalize_legal_text(FIXTURE)
    assert "revogado" not in normalized.vigente
    kinds = {mark.kind for mark in normalized.marks}
    assert "strikethrough" in kinds
    strike = next(m for m in normalized.marks if m.kind == "strikethrough")
    assert strike.status == "historical"
    assert "revogado" in strike.text


def test_vetado_nao_vira_chunk_vigente():
    chunks = parse_law_text(FIXTURE)
    articles = [chunk.article for chunk in chunks]
    assert articles == ["Art. 1º", "Art. 3º"]
    joined = "\n".join(chunk.text for chunk in chunks)
    assert "VETADO" not in joined
    assert "revogado" not in joined


def test_redacao_dada_fica_estruturada():
    normalized = normalize_legal_text(FIXTURE)
    redacao = next(m for m in normalized.marks if m.kind == "redacao_dada")
    assert redacao.status == "annotation"
    assert "14.133" in (redacao.citation or "")
    chunks = parse_law_text(FIXTURE)
    assert "Nova regra" in chunks[1].text


def test_vetado_em_linha_seguinte():
    text = "Art. 9º\n(VETADO)\nArt. 10. Vale.\n"
    chunks = parse_law_text(text)
    assert [c.article for c in chunks] == ["Art. 10"]
