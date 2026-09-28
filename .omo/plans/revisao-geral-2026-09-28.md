# Revisão geral — 28/09/2026 (`chore/revisao-geral-28-09`)

Objetivo: varredura de consistência/correção no estado pós-`3decf0b` (miss-hunter v1).
Fora de escopo: refactor especulativo, novas features, tuning de recall (exige régua humana).

## Frente A — Analyzer (núcleo de confiança)
- [ ] A1. `engine.py`: ordem das fases 2→2.2→2.3→2.4; hunter recebe `pending_reviews` pós-supervisor (altos virados não voltam como alvo — ok?).
- [ ] A2. `miss_hunter.py`: restore de snapshot mescla listas sem duplicar ids; `analyzed_items` restaurado; `finally` com `db.flush` mesmo se persist falhar.
- [ ] A3. `item_analysis.py`: hunter unitário/batch usam `MISS_HUNTER_SYSTEM_PROMPT`; `_truncate_content` sem duplicar warning do fluxo unitário.
- [ ] A4. `analysis_persistence.py`: gate aplicado também aos achados hunter (via `persist_item_outcomes` — confirmar, não duplicar).
- [ ] A5. `evidence_gate.py`: ordem OPS→NIT→G1→G3→G2→G4 preservada; sem barra nova que quebre `test_tp_real_passa`.
- [ ] A6. `review.py`/`analysis_phases.py`: hunter passa por `_run_cross_review` + supervisor (confirmar no engine).

## Frente B — RAG / Jobs / LLM / Config
- [ ] B1. `retriever.py`/`backends.py`: fallback ILIKE logado; quarentena TCU respeitada no caminho hunter (usa `retrieve` da fase 1 — ok?).
- [ ] B2. `jobs/queue.py` + `worker.py`: hunter roda dentro do job de análise (sem enqueue separado — sem lease extra; travar se worker timeout?).
- [ ] B3. `llm/factory.py` + `provider.py`: hunter usa o mesmo `llm` failover (sem cliente novo — confirmar).
- [ ] B4. `config.py` + `.env.example` + `docker-compose.yml` (backend+worker): `MISS_HUNTER_*` presentes nos 3; default OFF nos 3.
- [ ] B5. Conftest hermética: `MISS_HUNTER_ENABLED` default False já blinda a suíte (confirmar que nenhum teste existente muda de comportamento).

## Frente C — Frontend / Docs
- [ ] C1. Copy honesta só em `ItemDetail.tsx`? Checar `report/[id]`, `analysis/[id]` e `guia` por "Nenhuma inconformidade" residual.
- [ ] C2. `docs/ops/piloto.md`: documentar flag do hunter (operador precisa descobrir).
- [ ] C3. `memory.md`: entrada 28/09 íntegra (linha própria, sem "sem commit" pendente).

## Gates de saída
- `pytest backend/tests` verde · `ruff check` limpo nos tocados · `tsc --noEmit` limpo.
- Sem commit na branch sem pedido explícito (report final + proposta de commit).
