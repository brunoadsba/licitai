from app.services.rag.query_terms import (
    content_terms,
    postgres_tsquery,
    word_terms,
)
from app.services.rag.article_query import filter_weak_fts_hits


def test_content_terms_ignora_citacao_da_lei():
    terms = content_terms("legalidade impessoalidade moralidade princípios Lei 14.133")
    assert "legalidade" in terms
    assert "impessoalidade" in terms
    assert "lei" not in terms
    assert "14133" not in terms
    assert "2021" not in terms


def test_postgres_and_usa_conteudo():
    q = postgres_tsquery("legalidade impessoalidade moralidade princípios Lei 14.133", "and")
    assert "&" in q
    assert "legalidade" in q
    assert "14133" not in q


def test_filter_weak_nao_conta_lei():
    kept = filter_weak_fts_hits(
        "legalidade impessoalidade moralidade princípios Lei 14.133",
        [{"chunk_text": "dispensa de licitação na Lei 14.133/2021", "article": "Art. 75"}],
    )
    assert kept == []
    strong = filter_weak_fts_hits(
        "legalidade impessoalidade moralidade princípios Lei 14.133",
        [{"chunk_text": "legalidade, impessoalidade, moralidade e eficiência", "article": "Art. 5º"}],
    )
    assert strong


def test_word_terms_separa_numero():
    assert "obras" in word_terms("dispensável 100.000 obras")
    assert "100000" not in word_terms("dispensável 100.000 obras")
    from app.services.rag.query_terms import number_terms

    assert "100000" in number_terms("dispensável 100.000 obras")
