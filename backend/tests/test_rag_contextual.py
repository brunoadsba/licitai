"""Chunks contextuais R2: cabeçalho no embedding, corpo intacto."""

from app.services.rag.loader import contextual_embedding_text


def test_contextual_prefixo_distingue_leis():
    a = contextual_embedding_text("Lei 14.133/2021", "Licitações", "Art. 6º", "", "texto")
    b = contextual_embedding_text("RILC-CODEBA", "Regulamento", "Art. 6º", "", "texto")
    assert a != b
    assert "14.133" in a and "RILC-CODEBA" in b
    assert a.endswith("texto")


def test_contextual_com_secao():
    t = contextual_embedding_text("L", "T", "Art. 1º", "CAPÍTULO I", "corpo")
    assert "CAPÍTULO I" in t and t.endswith("corpo")
