# Contexto e Memória do Projeto: Sistema Especialista em Análise de TR (SEI)

Fonte da verdade para continuar o trabalho sem perda de contexto. Histórico
cronológico completo (até 28/09/2026) em
[docs/archive/historico-memory-ate-2026-09-28.md](docs/archive/historico-memory-ate-2026-09-28.md) — movido, não apagado.

## 1. Visão geral

Sistema full-stack que analisa Termos de Referência de licitações (Leis
14.133/2021 e 13.303/2016, RILC, TCU, AGU, CGU). Piloto CODEBA, single-user:
elaborador sobe o TR → revisa só alto/crítico + Art. 6º faltante → sai com
pacote SEI e/ou TR corrigido. Stack: Next.js 14 + React 18 + Tailwind 3
(frontend), FastAPI + SQLAlchemy async + Alembic (backend), PostgreSQL 16 +
pgvector (Compose), SQLite só em `APP_ENV=development`. IA: 4 agentes
especializados (jurídico, técnico, redação, estrutural) + orquestrador
(`asyncio.gather`, dedup, `agent_origin`) + RAG híbrido (FTS Postgres AND/OR +
embeddings) + revisão cruzada fail-closed + supervisor determinístico
(evidence_gate OPS→NIT→G1→G3→G2→G4) + miss-hunter opt-in (2ª passada nos itens
"ok"). Jobs duráveis no Postgres + worker asyncio (`python -m app.worker`).

## 2. Regras invioláveis

- Sigilo fail-closed: classificação `NULL` = sigiloso; cloud bloqueada p/
  sigiloso/sem classificação (422 / job não-retriável); sem Ollama não roda.
- Cópia SEI só com `review_status ∈ {aprovada, ajustada}`.
- TCU sem URL oficial em quarentena (`quarantine-0B`): fora da busca, do
  `legal_basis`, do parecer e do SEI.
- Análises/comparações só avançam com o worker no ar.
- Auth do piloto = BFF Next (`/api/proxy/*`, valida mesma origem) +
  `API_TOKEN` server-side; nunca `NEXT_PUBLIC_API_TOKEN`.
- CI GitHub desligado (`ci.yml.disabled`) — só religar com pedido explícito.
- Arquivo >300 LOC: ao tocar, extrair módulo no mesmo PR (sem refactor
  especulativo). Exceções atuais: `llm/provider.py` (376),
  `analyzer/evidence_gate.py` (352), `rag/loader.py` (339), `rag/semantic.py`
  (323), `analyzer/analysis_phases.py` (319), `analysis_persistence.py` (315),
  `useAnalysisPage.ts` (312), `api/documents.py` (311).

## 3. Estado atual (28/09/2026)

- Branch: só `main` (== `origin/main`); feature branches apagadas após merge.
- Suíte backend **435 passed** · `tsc --noEmit` limpo · `ruff check` limpo
  (format não é gate). Schema esperado: `20260924_004`.
- Fase 4 (28/09, `chore/higiene-memory`): worktree `.kilo` removida,
  caches limpos, `.kilo/` no `.gitignore`, `licitacao.db` mantido (default dev),
  memory consolidado (690→~100 linhas, histórico em
  [docs/archive/historico-memory-ate-2026-09-28.md](docs/archive/historico-memory-ate-2026-09-28.md)).
  4.2 resolvido: warnings de thread vinham de engines SQLite sem `dispose`
  (`fase4`/`fase8`/`sei_pack` + outros) — `conftest.py` agora rastreia e descarta
  todo engine após cada teste; suíte passa com warnings de thread como erro.
- Frontend: Next **14.2.35** (audit residual aceito e documentado em
  [docs/ops/auditoria-deps-2026-09.md](docs/ops/auditoria-deps-2026-09.md);
  rotina mensal `scripts/audit_deps.sh`).
- Cadeia free: gemini → groq → mistral → openrouter (+ Ollama `qwen3:8b`
  local p/ sigiloso). `.env` operacional: `ANALYSIS_BATCH_SIZE=5`,
  `ANALYSIS_MAX_LLM_CALLS=24`, `SUPERVISOR_REREVIEW_HIGH=true`,
  `MISS_HUNTER_ENABLED=false` (cap 10, fora do orçamento, pula com
  `budget_truncated`). Com TPM apertado (Groq 413), baixar o lote p/ 1–2.
- Qualidade medida: Groq golden R 0,56 / P 1,0; FTS piloto r@5 0,929;
  TR real (golden draft `e2e/golden/real/tr_pabx.json`): `290c7061` recall
  0,67 fp 0/2, `8cdafd60` recall 0,00 fp 1/2 (FP 4.9.2 persiste no batch).
  Medida real exige re-run + anotação humana.
  ([docs/ops/recall-tr-real-2026-09.md](docs/ops/recall-tr-real-2026-09.md))
- Confiança: roda sem quebrar ALTA; precisão MÉDIA-ALTA; **recall o ponto
  vermelho**; free exige babysitting. Bom piloto **assistido**, não p/
  confiança cega.
- Jobs PABX de referência: `8cdafd60` (batch5, completed, nota 9.3),
  `f9648727` (parcial 186/257). Gate 14 dias: janela fechou 28/09 —
  decisão Go/No-Go com o Bruno.

## 4. Como executar

```bash
./scripts/up.sh            # compose up + smoke (UI :3000, API :8000)
./scripts/up.sh --build    # obrigatório após mudar frontend/imagem (sem bind mount)
./scripts/down.sh          # para sem apagar pgdata
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q
cd frontend && npx tsc --noEmit
E2E_BASE_URL=http://127.0.0.1:8000 PYTHONPATH=backend pytest e2e/tests
E2E_LIVE=1 E2E_BASE_URL=http://127.0.0.1:3000 npx playwright test e2e/bff-origin.spec.ts
./scripts/audit_deps.sh    # mensal; só reporta
```

## 5. Pendências (lista única)

- Humano: revisar 5 achados pendentes (DDR alínea "e" + 1.1); decisão do gate
  14d; anotar 1 TR real (régua do recall); colar SEI em minuta de teste;
  chaves pagas só se a Fase 3 mandar (`ANTHROPIC_API_KEY` c/ teto,
  SiliconFlow/Z.ai/Cohere/NVIDIA, permissão HF); URLs oficiais TCU (sair da
  quarentena); visto jurídico da amostra.
- Código: teste ao vivo do batch 1–2 no reset da cota; upload-tr full
  happy-path (redirect ok, conclusão travou na cota 28/09); bumps
  `starlette`/`multipart`/`pdfminer` em branch própria; Vitest p/ libs puras
  (baixa prioridade); `AnthropicProvider` só se Fase 3 mandar.
- Operação: backup drill; `licitacao.db` da raiz é o default dev
  (`config.py:32`, gitignored) — manter.

## 6. Armadilhas conhecidas (1 linha cada)

- `request.nextUrl.origin` normaliza p/ `localhost` enquanto o piloto acessa
  via `127.0.0.1` — BFF compara com equivalência loopback+Host (não simplificar).
- `.env` local com chaves/lote vaza p/ testes — `conftest.py` zera tudo e fixa
  lote 1 + hunter off (manter a blindagem ao adicionar flags).
- `rag_eval_baseline.json` se reescreve sozinho (harness) — ruído, sem impacto.
- Python do sistema WSL corrompido — backend só no venv (`backend/.venv`).
- `next start` não funciona com `output: standalone` — produção é via Docker.
- Frontend sem bind mount — rebuild a cada mudança de UI.
- Extensão SEI só faz GET no BFF — allowlist `BFF_ALLOWED_ORIGINS` cobre futuro.
- `ANALYSIS_BATCH_SIZE=5` estoura TPM free (Groq 413 >8000) — rotina usa 1–2.
- Docs vivos: [docs/ops/piloto.md](docs/ops/piloto.md),
  [docs/guia-usuario.md](docs/guia-usuario.md), este arquivo,
  [frontend/DESIGN.md](frontend/DESIGN.md). Planos em `.omo/plans/`.
