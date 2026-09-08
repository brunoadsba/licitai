"""Testes de confiabilidade — Art.6, SEI filter, RetrievedChunk.id."""

from app.api.analysis import SEI_APPLICABLE_STATUSES, _filter_corrections
from app.services.generator.validator import validate_tr_completeness
from app.services.legal.art6_xxiii import ART6_XXIII_ELEMENTS, art6_keys
from app.services.rag.retriever import RetrievedChunk


def test_art6_tem_dez_alineas_a_j():
    keys = art6_keys()
    assert len(keys) == 10
    assert [e.alinea for e in ART6_XXIII_ELEMENTS] == list("abcdefghij")
    forbidden = {"garantia", "infracoes_sancoes", "cronograma", "sancoes"}
    assert forbidden.isdisjoint(set(keys))


def test_validate_tr_completeness_usa_art6_canonico():
    faltantes = validate_tr_completeness([])
    assert set(faltantes) == set(art6_keys())


def test_sei_filter_so_aprovada_ajustada():
    class C:
        def __init__(self, status: str):
            self.review_status = status

    items = [C("aprovada"), C("ajustada"), C("rejeitada"), C("pendente")]
    filtered = _filter_corrections(items, for_sei=True)
    assert {c.review_status for c in filtered} == SEI_APPLICABLE_STATUSES


def test_retrieved_chunk_tem_id():
    chunk = RetrievedChunk(
        id="abc-123",
        law_number="Lei 14.133/2021",
        law_title="Nova Lei",
        article="Art. 6º",
        section="",
        text="texto",
        score=1.0,
    )
    assert chunk.id == "abc-123"
