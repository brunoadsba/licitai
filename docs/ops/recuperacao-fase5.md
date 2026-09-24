# Fase 5 — Recuperação PostgreSQL e contexto hierárquico

## O que mudou

- `legal_chunks.search_tsv` (tsvector português + `unaccent`) com GIN e trigger.
- `_search_postgres` usa `to_tsquery` AND (conteúdo) com fallback OR; ILIKE só se o índice faltar.
- Consulta textual sempre busca `rag_candidates` e aplica `heuristic_rerank` (não corta em top-k no SQL).
- Termos de citação (`lei`, `14.133`, `2021`) não entram no FTS nem no filtro fraco.
- Consulta direta por artigo (`art. 37`, `artigo 6`) no SQLite e no Postgres.
- `expand_hierarchical` entrega caput/ancestrais com orçamento de tokens.
- Cache de retrieve keyed por `corpus_version` + classificação, com teto de 256 e invalidação na reingestão.

## Schema

Head esperado: `20260924_004`.

## Homologação

1. `alembic upgrade head` no backend.
2. `python -m scripts.inspect_pgvector` para tipo/índice/plano.
3. `PYTHONPATH=. python scripts/eval_corpus_real.py --piloto --check-baseline --baseline eval/baseline.piloto.json` (tolerância 2 pp).

Piloto em 2026-09-24: schema `20260924_004`, 599 `search_tsv`, plano usa `ix_legal_chunks_search_tsv`. Baseline textual após AND/OR + rerank em `rag_candidates`: r@5 **0.929** (antes 0.357). `documentos_longos` ainda 0. Sem regressão em `sem_resposta` / `prompt_injection`.

`embedding_vector` pode ser preenchido com `python scripts/backfill_embedding_vector.py --apply` (cópia do JSON; sem HNSW — 3072 dims). Não reduzir dimensão sem medir recall.

O índice legado `legal_documents`/`legal_chunks` continua o caminho de retrieve. O sidecar da Fase 4 só alimenta a expansão hierárquica.
