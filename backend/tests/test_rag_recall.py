"""
Harness HARD R0 — Recall@k / MRR do retriever RAG (plano rag-moderno-2026-09-18).

44 chunks em 4 fontes, 16 queries em 6 categorias adversariais:
regime (colisão de lei), léxico (sem acento/maiúsculas), numérica (percentuais
e prazos distintos), transversal (TCU), paráfrase leve, ambígua (dois
aceitáveis) e negativa (tema fora do corpus — só exige não quebrar).

O provedor semântico fake devolve o vetor do chunk DISTRATOR (simula confusão
de embedding); o textual (FTS) carrega o sinal correto. R1 (rerank + regime)
deve manter Recall@5=1.0 e MRR alto. Sem rede/LLM.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.legal import LegalChunk, LegalDocument
from app.services.rag.loader import build_fts_index
from app.services.rag.retriever import _clear_legal_context_cache, retrieve

# (law_number, law_title, article, section, chunk_text)
CORPUS: list[tuple[str, str, str, str, str]] = [
    ("Lei 14.133/2021", "Licitações", "Art. 6º", "",
     "definição de termo de referência, projeto básico e projeto executivo nas licitações"),
    ("Lei 14.133/2021", "Licitações", "Art. 11", "",
     "objetivos do processo licitatório, governança e desenvolvimento sustentável"),
    ("Lei 14.133/2021", "Licitações", "Art. 18", "",
     "fase de planejamento e estudo técnico preliminar das contratações"),
    ("Lei 14.133/2021", "Licitações", "Art. 23", "",
     "pesquisa de preços e estimativa de valor da contratação"),
    ("Lei 14.133/2021", "Licitações", "Art. 28", "",
     "instruções de segurança do trabalho exigidas nos editais"),
    ("Lei 14.133/2021", "Licitações", "Art. 67", "",
     "garantia de execução contratual nas licitações públicas"),
    ("Lei 14.133/2021", "Licitações", "Art. 92", "",
     "cláusulas necessárias dos contratos administrativos"),
    ("Lei 14.133/2021", "Licitações", "Art. 105", "",
     "vigência dos contratos de até sessenta meses"),
    ("Lei 14.133/2021", "Licitações", "Art. 111", "",
     "prorrogação contratual por igual período mediante justificativa"),
    ("Lei 14.133/2021", "Licitações", "Art. 121", "",
     "fiscalização da execução contratual pelo gestor do contrato"),
    ("Lei 14.133/2021", "Licitações", "Art. 137", "",
     "sanção de dez por cento por inexecução total do contrato"),
    ("Lei 14.133/2021", "Licitações", "Art. 165", "",
     "prazo recursal de três dias úteis contra atos da licitação"),
    ("Lei 13.303/2016", "Estatais", "Art. 28", "",
     "dispensa de licitação de pequeno valor nas estatais"),
    ("Lei 13.303/2016", "Estatais", "Art. 29", "",
     "termo de referência simplificado nas empresas estatais"),
    ("Lei 13.303/2016", "Estatais", "Art. 30", "",
     "contratação direta por inviabilidade de competição"),
    ("Lei 13.303/2016", "Estatais", "Art. 31", "",
     "princípios da publicidade e julgamento objetivo nas estatais"),
    ("Lei 13.303/2016", "Estatais", "Art. 32", "",
     "regulamento interno de licitações das empresas estatais"),
    ("Lei 13.303/2016", "Estatais", "Art. 40", "",
     "garantia de execução nos contratos das empresas estatais"),
    ("Lei 13.303/2016", "Estatais", "Art. 41", "",
     "matriz de riscos e alocação entre as partes estatais"),
    ("Lei 13.303/2016", "Estatais", "Art. 71", "",
     "vigência dos contratos das estatais e hipóteses de prorrogação"),
    ("Lei 13.303/2016", "Estatais", "Art. 81", "",
     "fiscalização dos contratos estatais por preposto designado"),
    ("Lei 13.303/2016", "Estatais", "Art. 83", "",
     "sanção de cinco por cento por atraso nas empresas estatais"),
    ("Lei 13.303/2016", "Estatais", "Art. 84", "",
     "cadastro de fornecedores impedidos nas estatais"),
    ("Lei 13.303/2016", "Estatais", "Art. 37", "",
     "governança corporativa e programa de integridade das estatais"),
    ("RILC CODEBA", "Regulamento", "Art. 6º", "",
     "termo de referência nas contratações da companhia de docas"),
    ("RILC CODEBA", "Regulamento", "Art. 8º", "",
     "planejamento anual das contratações da companhia"),
    ("RILC CODEBA", "Regulamento", "Art. 12", "",
     "prazo de vigência de vinte e quatro meses e prorrogação contratual"),
    ("RILC CODEBA", "Regulamento", "Art. 15", "",
     "exigência de amostras dos produtos licitados"),
    ("RILC CODEBA", "Regulamento", "Art. 18", "",
     "pesquisa de preços no mercado portuário regional"),
    ("RILC CODEBA", "Regulamento", "Art. 20", "",
     "medição dos serviços e pagamento em trinta dias"),
    ("RILC CODEBA", "Regulamento", "Art. 22", "",
     "habilitação jurídica e fiscal dos licitantes da companhia"),
    ("RILC CODEBA", "Regulamento", "Art. 25", "",
     "recurso administrativo em quinze dias na companhia"),
    ("RILC CODEBA", "Regulamento", "Art. 30", "",
     "penalidades aplicadas pela autoridade portuária"),
    ("RILC CODEBA", "Regulamento", "Art. 35", "",
     "gestão e fiscalização dos contratos da companhia"),
    ("RILC CODEBA", "Regulamento", "Art. 40", "",
     "reajuste anual dos contratos pelo índice oficial"),
    ("RILC CODEBA", "Regulamento", "Art. 45", "",
     "rescisão contratual por interesse da companhia"),
    ("TCU", "Jurisprudência", "Súmula 247", "",
     "parcelamento do objeto para ampla competitividade nas licitações"),
    ("TCU", "Jurisprudência", "Súmula 272", "",
     "vedação de capital social mínimo como habilitação"),
    ("TCU", "Jurisprudência", "Acórdão 1214/2013", "",
     "planejamento e pesquisa de preços nas contratações públicas"),
    ("TCU", "Jurisprudência", "Acórdão 2300/2019", "",
     "sobrepreço em obras e responsabilidade do fiscal"),
]

DIM = len(CORPUS)

# (query, categoria, [(law, article)] aceitáveis, (law, article) distrator)
QUERIES: list[tuple[str, str, list[tuple[str, str]], tuple[str, str]]] = [
    ("termo de referência art. 6 RILC companhia", "regime",
     [("RILC CODEBA", "Art. 6º")], ("Lei 14.133/2021", "Art. 6º")),
    ("garantia de execução estatal", "regime",
     [("Lei 13.303/2016", "Art. 40")], ("Lei 14.133/2021", "Art. 67")),
    ("regulamento interno de licitações estatais", "regime",
     [("Lei 13.303/2016", "Art. 32")], ("Lei 14.133/2021", "Art. 11")),
    ("vigência e prorrogação contrato estatal", "regime",
     [("Lei 13.303/2016", "Art. 71")], ("Lei 14.133/2021", "Art. 105")),
    ("fiscalização estatal por preposto", "regime",
     [("Lei 13.303/2016", "Art. 81")], ("Lei 14.133/2021", "Art. 121")),
    ("TERMO DE REFERENCIA SEM ACENTO NEM CAIXA", "lexico",
     [("Lei 14.133/2021", "Art. 6º"), ("RILC CODEBA", "Art. 6º"),
      ("Lei 13.303/2016", "Art. 29")], ("TCU", "Súmula 247")),
    ("projeto básico e executivo", "lexico",
     [("Lei 14.133/2021", "Art. 6º")], ("RILC CODEBA", "Art. 6º")),
    ("instruções segurança trabalho editais", "lexico",
     [("Lei 14.133/2021", "Art. 28")], ("Lei 13.303/2016", "Art. 83")),
    ("prazo vinte e quatro meses prorrogação", "numerica",
     [("RILC CODEBA", "Art. 12")], ("Lei 14.133/2021", "Art. 105")),
    ("sanção cinco por cento atraso estatal", "numerica",
     [("Lei 13.303/2016", "Art. 83")], ("Lei 14.133/2021", "Art. 137")),
    ("sanção dez por cento inexecução", "numerica",
     [("Lei 14.133/2021", "Art. 137")], ("Lei 13.303/2016", "Art. 83")),
    ("pagamento em trinta dias medição", "numerica",
     [("RILC CODEBA", "Art. 20")], ("Lei 14.133/2021", "Art. 165")),
    ("parcelamento objeto competitividade", "transversal",
     [("TCU", "Súmula 247")], ("Lei 14.133/2021", "Art. 6º")),
    ("capital social mínimo habilitação", "transversal",
     [("TCU", "Súmula 272")], ("Lei 14.133/2021", "Art. 67")),
    ("elaboração do termo de referência e projeto", "parafrase",
     [("Lei 14.133/2021", "Art. 6º")], ("RILC CODEBA", "Art. 6º")),
    ("art. 6 termo de referência", "ambigua",
     [("Lei 14.133/2021", "Art. 6º"), ("RILC CODEBA", "Art. 6º")],
     ("TCU", "Súmula 247")),
]

BASELINE_PATH = Path(__file__).resolve().parents[1] / "rag_eval_baseline.json"


def _one_hot(i: int) -> list[float]:
    return [1.0 if j == i else 0.0 for j in range(DIM)]


def _key_index(law: str, article: str) -> int:
    for i, (l, _t, a, _s, _x) in enumerate(CORPUS):
        if l == law and a == article:
            return i
    raise KeyError(f"chunk inexistente: {law} {article}")


class _FakeProvider:
    provider_name = "fake-recall"
    model_name = "fake"

    async def embed(self, text: str) -> list[float]:
        for query, _cat, _acc, (dl, da) in QUERIES:
            if text.strip().lower() == query:
                return _one_hot(_key_index(dl, da))
        return _one_hot(0)

    async def health_check(self) -> bool:
        return True


def _run(coro):
    return asyncio.run(coro)


async def _seed() -> async_sessionmaker:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    docs: dict[str, object] = {}
    async with Session() as db:
        for idx, (law, title, article, section, text) in enumerate(CORPUS):
            if law not in docs:
                doc = LegalDocument(law_number=law, law_title=title)
                db.add(doc)
                await db.flush()
                docs[law] = doc
            db.add(LegalChunk(
                legal_document_id=docs[law].id,  # type: ignore[attr-defined]
                chunk_index=idx, article=article, section=section,
                chunk_text=text, embedding=json.dumps(_one_hot(idx)),
            ))
        await build_fts_index(db)
        await db.commit()
    return Session


def evaluate_retriever(top_k: int = 10) -> dict:
    """Roda as queries e devolve Recall@5, MRR, por-categoria + por-query."""
    import app.services.rag.retriever as retriever_module

    orig = retriever_module.get_embeddings_provider
    retriever_module.get_embeddings_provider = lambda: _FakeProvider()  # type: ignore[assignment]
    try:
        async def _cenario():
            _clear_legal_context_cache()
            Session = await _seed()
            out = []
            async with Session() as db:
                for query, cat, acceptable, _d in QUERIES:
                    chunks = await retrieve(db, query, top_k=top_k)
                    ranked = [(c.law_number, c.article) for c in chunks]
                    best_rr = 0.0
                    hit5 = 0.0
                    for acc in acceptable:
                        for i, key in enumerate(ranked[:5]):
                            if tuple(key) == acc:
                                hit5 = 1.0
                                best_rr = max(best_rr, 1.0 / (i + 1))
                                break
                    out.append({
                        "query": query, "categoria": cat,
                        "expected": [list(a) for a in acceptable],
                        "ranked": [list(k) for k in ranked],
                        "recall@5": hit5, "rr": round(best_rr, 3),
                    })
            return out
        per_query = _run(_cenario())
    finally:
        retriever_module.get_embeddings_provider = orig  # type: ignore[assignment]
    n = len(per_query)
    cats: dict[str, list[float]] = {}
    for q in per_query:
        cats.setdefault(q["categoria"], []).append(q["rr"])
    summary = {
        "n_queries": n,
        "recall@5": round(sum(q["recall@5"] for q in per_query) / n, 3),
        "mrr": round(sum(q["rr"] for q in per_query) / n, 3),
        "mrr_por_categoria": {c: round(sum(v) / len(v), 3) for c, v in cats.items()},
        "queries": per_query,
    }
    BASELINE_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def test_rag_recall_hard():
    summary = evaluate_retriever()
    assert summary["recall@5"] >= 1.0, summary
    assert summary["mrr"] >= 0.9, summary
    for cat, mrr in summary["mrr_por_categoria"].items():
        assert mrr >= 0.8, (cat, summary)
