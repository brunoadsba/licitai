# Avaliação curada (Fase 2)

Conjunto e runner locais. O GitHub Actions permanece desligado (`ci.yml.disabled`).

- Casos: `backend/eval/cases.json` (14 categorias, inclusive injection e TCU em quarentena).
- Semente reproduzível: `backend/eval/seed_corpus.json`.
- Runner: `backend/scripts/eval_corpus_real.py`.
- Baseline da semente: `backend/eval/baseline.ci.json` (Recall@5 1.0).
- Baseline do piloto (599 chunks): `backend/eval/baseline.piloto.json` (Recall@5 0.357 após FTS).
- `legal_review` no conjunto: **pendente** de visto jurídico.

A busca textual do Postgres usa FTS (`tsvector` português + GIN). A semente continua pontuando alto; o corpus cheio subiu de 0.214 (ILIKE) para 0.357. O visto jurídico do conjunto permanece pendente.

## Como rodar

No host, a partir de `backend/`:

```bash
# Semente (reproduz o número da baseline.ci.json)
PYTHONPATH=. python scripts/eval_corpus_real.py --seed --check-baseline --baseline eval/baseline.ci.json

# Corpus do piloto (Compose no ar)
PYTHONPATH=. python scripts/eval_corpus_real.py --piloto --database-url "$DATABASE_URL"
```

`--check-baseline` falha se Recall@5 cair mais de 2 pontos percentuais por categoria em relação ao arquivo informado.

Não reative o CI no GitHub sem pedido explícito.