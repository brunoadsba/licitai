"""Testes do rerank heurístico R1 (puro, sem IO/LLM)."""

from app.services.rag.rerank import (
    chunk_regime,
    detect_query_regime,
    heuristic_rerank,
)


def _row(law: str, article: str, text: str) -> dict:
    return {"law_number": law, "article": article, "section": "",
            "chunk_text": text, "score": 0.01}


def test_regime_query_e_chunk():
    assert detect_query_regime("termo de referência RILC companhia") == "13.303"
    assert detect_query_regime("pregão eletrônico 14.133") == "14.133"
    assert detect_query_regime("texto neutro") is None
    assert chunk_regime(_row("RILC-CODEBA", "Art. 6º", "x")) == "13.303"
    assert chunk_regime(_row("Lei 14.133/2021", "Art. 6º", "x")) == "14.133"
    assert chunk_regime(_row("Súmula 247/TCU", "", "x")) == "transversal"


def test_rerank_promove_regime_correto():
    rows = [
        _row("Lei 14.133/2021", "Art. 6º", "definição de termo de referência"),
        _row("RILC-CODEBA", "Art. 6º", "termo de referência na companhia"),
    ]
    out = heuristic_rerank("termo de referência art. 6 RILC companhia", rows)
    assert out[0]["law_number"] == "RILC-CODEBA"
    assert out[0]["rerank_score"] > out[1]["rerank_score"]


def test_rerank_vazio():
    assert heuristic_rerank("qualquer", []) == []


class _FakeLLM:
    def __init__(self, payload: str):
        self.payload = payload

    async def generate(self, _system: str, _user: str) -> str:
        return self.payload


def test_llm_rerank_reordena():
    import asyncio

    from app.services.rag.rerank import llm_rerank

    rows = [
        _row("Lei 14.133/2021", "Art. 6º", "definição de termo de referência"),
        _row("RILC-CODEBA", "Art. 6º", "termo de referência na companhia"),
    ]
    llm = _FakeLLM('{"scores": [{"i": 0, "s": 0}, {"i": 1, "s": 2}]}')
    out = asyncio.run(llm_rerank(llm, "RILC companhia", rows, top_k=2))
    assert out[0]["law_number"] == "RILC-CODEBA"


def test_llm_rerank_fail_open():
    import asyncio

    from app.services.rag.rerank import llm_rerank

    rows = [_row("A", "Art. 1º", "x"), _row("B", "Art. 2º", "y")]
    llm = _FakeLLM("resposta inválida sem json")
    assert asyncio.run(llm_rerank(llm, "q", rows)) == rows
    assert asyncio.run(llm_rerank(None, "q", rows)) == rows
