# Relatório RAG moderno — antes/depois (18/09/2026, branch `feat/rag-moderno-18-09`)

Harness: `backend/tests/test_rag_recall.py` (12 chunks, 4 fontes, 6 queries com
colisão proposital + distrator semântico). Sem rede/LLM.

| Métrica | R0 baseline (RRF puro) | R1 (rerank heurístico) |
|---|---|---|
| Recall@5 | 0.833 | **1.0** |
| MRR | 0.331 | **1.0** |

Todas as 6 queries passam a ranquear o chunk esperado em 1º (ex.: query RILC →
RILC Art. 6º acima de 14.133 Art. 6º; “garantia estatal” → 13.303 Art. 40).

## O que entrou

- R0: `test_rag_recall.py`, `scripts/eval_rag.py`, `rag_eval_baseline.json`.
- R1: `services/rag/rerank.py` (heurístico), `retrieve()` 20 candidatos → top-k,
  flags `rag_candidates`/`rag_rerank_mode` (`off` = rollback).
- R2: `contextual_embedding_text()` + `ingest_embeddings.py` com cabeçalho e
  `embedding_dim`; reingestão do piloto pendente (script pronto, exige chaves).
- R3: `llm_rerank()` fail-open + fiação engine com trava sigiloso/cloud
  (default `heuristic`, LLM desligado); `claim_support_rate()` no evidence JSON.
- R4: este relatório. Docs/README do RAG ficam para o merge em `main`.

## Validação

- Backend: **292 passed**, LSP 0 erros, `tsc` limpo (sem mudança frontend).
- Sem regressão em `test_retriever.py` (fallback textual intacto).

## Pendente (piloto, com chaves/LLM)

1. Reingestão `ingest_embeddings.py` no Postgres piloto (gera vetores v2).
2. Re-run ouro 09-ti-pabx-nuvem: medir precisão nova (meta ≥0.80).
3. Decisão go/no-go do `rag_rerank_mode="llm"` pelo custo real.
