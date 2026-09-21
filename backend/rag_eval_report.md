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

## Piloto executado (21/09/2026, branch `feat/rag-moderno-18-09`)

Backup pré-reingestão: `/tmp/rag_corpus_backup.dump` (host).

1. **Reingestão v2: FEITA.** `embedding_dim` era NULL nos 599 (vetores v1);
   após NULL + `ingest_embeddings.py` (Gemini `gemini-embedding-001`):
   **599/599 dim 3072, 0 falhas**, ~9 min, sem 429.
2. **Latência real (Postgres, 20 queries domínio, `tmp/rag_probe.json`):
   p50 1,7s / p95 2,5s / max 2,6s** — p95 acima da meta <2s; driver é o
   embedding Gemini por query. Top-3 qualitativamente forte
   (ex.: "art 6" → Art. 6º em 1º; TCU → súmulas). Recall@5 formal ≥0.85
   aguarda rotulação humana dos top-3 salvos.
3. **Re-run ouro `09-ti-pabx-nuvem` (economic, analysis `e0d37c4e`):
   `completed_with_errors`, 12/257 itens** (teto `ANALYSIS_MAX_LLM_CALLS=24`).
   8 achados (3 alto / 4 baixo / 1 info); cross-review: 5 rejeitadas,
   2 aprovadas, 1 ajustada; `art6_coverage` 1.0; score 9.9/risco baixo.
   `claim_support` médio **1.0** (8/8 totalmente ancorados — métrica pode
   estar leniente; todos os rejeitados também deram total).
   Precisão humana nova aguarda revisão cega (meta ≥0.80).
4. **Custo modo LLM (5 queries, Groq `openai/gpt-oss-20b`): +1,9–12,3s por
   query**, overlap heurístico×LLM 2–4/5; em 1 caso ("art 6") o LLM tirou o
   Art. 6º do top-3 (**regressão**). Com o teto de 24 calls, o modo `llm`
   reduziria a cobertura de ~12 para ~8 itens.
   **Recomendação: NO-GO — manter `heuristic` (default).**
5. **Selo UI + trava + env entregues:** `claim_support` serializado e selo
   "n/m afirmações ancoradas" no `CorrectionCard` (frontend rebuildado);
   `llm_rerank_allowed_for_document()` + `test_rag_privacy.py`;
   `RAG_CANDIDATES`/`RAG_RERANK_MODE` no `.env.example`.
