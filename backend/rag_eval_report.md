# Relatório RAG moderno — antes/depois (18/09/2026, branch `feat/rag-moderno-18-09`)

Harness HARD: `backend/tests/test_rag_recall.py` (44 chunks, 4 fontes,
16 queries em 6 categorias: regime, léxico, numérica, transversal, paráfrase,
ambígua) + `test_rag_robustness.py` (determinismo, fallback, cache, hostis).
Sem rede/LLM.

| Métrica | R0 (RRF puro, 6 queries) | R1 (rerank, 6 queries) | HARD (16 queries) |
|---|---|---|---|
| Recall@5 | 0.833 | 1.0 | **1.0** |
| MRR | 0.331 | 1.0 | **1.0** |

O teste hard começou **falhando** (0.56/0.56) e expôs 3 fraquezas reais,
corrigidas no pipeline de produção: RRF com peso assimétrico → clássico
(pesos iguais); 20 candidatos → 50; FTS sem stopwords/stemming → stopwords PT
+ prefixo `*` + overlap por prefixo no rerank. Todas as 16 queries ranqueiam
o esperado em 1º, por categoria ≥0.8 (trava no teste).

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
