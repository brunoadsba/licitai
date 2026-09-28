# Briefing de auditoria — Grok 4.7 (28/09/2026)

Você tem acesso ao projeto inteiro. Sua missão: **auditoria adversarial do LicitAI como revisor sênior full-stack** — caçar bugs, furos de segurança/honestidade, desperdício e melhorias que destravam o piloto. Você NÃO executa navegador nem roda LLM pago — análise estática do código + docs.

## Contexto (leia primeiro)

- `memory.md` (fonte da verdade, ~130 linhas) + histórico em `docs/archive/historico-memory-ate-2026-09-28.md`
- Estado: `main` = `399e873` (UX-Confiança mergeada, tsc + 47 Vitest + 13 Playwright verdes). Working tree com golden v2 não commitado: `e2e/golden/real/tr_pabx.json` (3 TPs + 18 tripwires, 17 pendentes rejeitados 0A/17R), `e2e/golden/real/anotacao_pabx_pendentes.md`, `docs/ops/recall-tr-real-2026-09.md`, `memory.md`
- Stack: Next.js 14 + React 18 + Tailwind 3 / FastAPI py3.12 + SQLAlchemy async + Alembic / Postgres 16 + pgvector (Compose, `sei-db`, base `sei_analise`, hoje **zero análises**) / IA: Groq→Gemini→Mistral→OpenRouter + Ollama `qwen3:8b` p/ sigiloso
- Piloto CODEBA single-user: elaborador sobe TR → revisa alto/crítico + Art. 6º → pacote SEI. Guia em `docs/guia-usuario.md`, ops em `docs/ops/piloto.md`
- Regras invioláveis: sigilo fail-closed (`NULL`=sigiloso, cloud bloqueada 422), cópia SEI só `aprovada/ajustada`, TCU sem URL em quarentena fora da busca, worker obrigatório, CI desligado (`ci.yml.disabled`), arquivo >300 LOC extrai módulo ao tocar

## Escopo (projeto inteiro, nesta ordem de prioridade)

1. `backend/app/services/analyzer/` (orquestrador, evidence_gate, miss-hunter, phases) + `backend/app/services/rag/` + `backend/app/services/llm/`
2. `backend/app/api/`, `backend/app/worker*`, `backend/app/services/parser/`, `backend/app/services/jobs/`
3. `frontend/src/components/analysis/`, `frontend/src/components/report/`, `frontend/src/app/report/[id]/`, `frontend/src/lib/calibration.ts`, `frontend/src/lib/confidence.ts`
4. `backend/scripts/benchmark_offline.py`, `e2e/golden/real/`, `backend/tests/test_golden.py`
5. `docker-compose.yml`, `.env.example`, `scripts/up.sh`, `docs/ops/deploy.md`, `docs/ops/auth-piloto.md`

## O que caçar (com arquivo:linha e prova)

1. **Bug funcional:** fila/jobs que travam sem worker; retomada/undo com estado parcial; teclado/foco que perde contexto; paginação/Filtros do BFF; parser que numera alínea como `a-2`/`b-3` (já visto no golden); `analyzed>total`, `total=0`, `evidence` nula
2. **Segurança:** vazamento de `API_TOKEN` no browser (`NEXT_PUBLIC_*`), BFF sem checagem de origem, upload sem magic-bytes/allowlist, `sigiloso` escapando p/ cloud, quarentena TCU furada no `legal_basis`/parecer/SEI, CORS/rate-limit/CSP frouxos
3. **Honestidade:** número sem fonte, nota seca em relatório parcial (<95% sem faixa), aviso longe do número (print decapita), copy absoluta ("garante/sempre/100%"), chip neutro parecendo selo, staleness sem efeito, recall v1 citado como se fosse real
4. **Custo/performance:** `ANALYSIS_BATCH_SIZE=5` estourando TPM Groq 413, `SUPERVISOR_REREVIEW_HIGH` e `MISS_HUNTER_ENABLED` sem cap visível, N+1 no Postgres, FTS sem índice, embeddings sem HNSW, frontend sem rebuild (sem bind mount)
5. **Melhorias que destravam:** o que impede re-medir recall v2 com zero análises; o que impede ligar miss-hunter e comparar; o que impede colar SEI real sem surpresa; top deuda técnica que trava o gate 14d

## O que NÃO fazer

- Não propor redesign, migração Next 15, K8s, multi-tenant/OIDC, fine-tune, LangGraph ou telemetria
- Não reabrir golden v2 (0/17) nem os 3 TPs de 16/09 sem prova no PDF `fixtures/trs-codeba/piloto-unico/09-ti-pabx-nuvem.pdf` via parser (`parse_pdf` + `structure_items`)
- Não pedir chave paga, CI ou bump de dependência sem mostrar o ganho medido
- Não repetir o QA anterior (`docs/qa-ux-grok-2026-09-28.md`, 16 itens já aplicados) salvo regressão com prova

## Formato da resposta (sem floreio)

Tabela: `| # | arquivo:linha | severidade (bloqueante/alto/médio/baixo) | tipo (bug/segurança/honestidade/custo/melhoria) | problema (1 frase) | sugestão concreta (1-2 linhas) |`

Depois:
- **Top 5** por custo/benefício (o que eu faria primeiro e por quê, 1 linha cada)
- **Veredito único:** `APROVADO` / `APROVADO COM RESSALVAS` (listar) / `REPROVADO` (listar bloqueantes)
- **Não-auditado:** o que você não conseguiu cobrir e por quê (1 linha cada)
