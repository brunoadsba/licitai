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
"ok") + copiloto consultivo (dossiê do TR quando o modelo recusa). Jobs
duráveis no Postgres + worker asyncio (`python -m app.worker`).

## 2. Regras invioláveis

- Sigilo fail-closed: classificação `NULL` = sigiloso; cloud bloqueada p/
  sigiloso/sem classificação (422 / job não-retriável); sem Ollama não roda.
- Cópia SEI só com `review_status ∈ {aprovada, ajustada}` escrito pelo PATCH
  humano. O revisor LLM grava `evidence.machine_review` e deixa `pendente`
  (`rejeitada` automática continua fora do SEI e da fila).
- TCU sem URL oficial em quarentena (`quarantine-0B`): fora da busca, do
  `legal_basis`, do parecer e do SEI.
- Análises/comparações só avançam com o worker no ar.
- Auth do piloto = BFF Next (`/api/proxy/*`, valida mesma origem) +
  `API_TOKEN` server-side; nunca `NEXT_PUBLIC_API_TOKEN`.
- CI GitHub desligado (`ci.yml.disabled`) — só religar com pedido explícito.
- Arquivo >300 LOC: ao tocar, extrair módulo no mesmo PR (sem refactor
  especulativo). Exceções atuais: `llm/provider.py` (376),
  `analyzer/evidence_gate.py` (352), `rag/loader.py` (339), `rag/semantic.py`
  (323), `analysis_persistence.py` (315),
  `useAnalysisPage.ts` (312), `api/documents.py` (311).

## 3. Estado atual (29/09/2026)

- Branch: `main` após merge de `feat/chat-dossie-copiloto`. Spike
  `feat/fetch-pncp-trs` segue sem merge (commit `240b1bc` no remoto).
- Suíte: última completa **447** backend · **49** Vitest (29/09) ·
  `tsc --noEmit` limpo. Schema esperado: `20260924_004`.
- Copiloto dossiê (29/09): `compose_sources` reserva item/correção/parecer;
  recusa, falha de LLM ou resposta só de lei cai em `aplicar_dossie`;
  pergunta de confiabilidade responde `PRODUCT_ANSWER` sem modelo;
  histórico de 6 turnos no prompt; chips não repetem a pergunta. Testes em
  `backend/tests/test_chat_intel.py`.
- Gate 14d (29/09): **Go**. Sem retorno dos colegas, o Bruno busca TRs no
  SEI nesta semana. [docs/ops/gate-piloto-14d.md](docs/ops/gate-piloto-14d.md).
- Jev (TypeSafe) avaliado 29/09: **não integrar**. API cloud quebra sigilo
  fail-closed; RAG já filtra corpus pequeno; risco/severidade já são
  determinísticos; calibração ruim em rating de qualidade.
- UX-Confiança (28/09, mergeado): página `/confianca`
  (números com fonte + staleness), nota calibrada por cobertura (<95% = faixa)
  em `ReportScores`, retomada da fila por id, chips de evidência, teclado
  (a/r/j/n/?) + undo inline, microcopy sem absolutos. QA externo (Grok,
  REPROVADO→16 correções aplicadas: amber claro, undo, foco, chips, números).
  E2E novos verdes (confianca, report-band, guided-keys).
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
- Correção da auditoria (28/09): SEI não sai de aprovação da máquina; undo
  devolve o texto; quarentena aceita `nº`/`n°`/`n.`; alínea fica no pai
  (`4.3.4.a`); Ollama default `host.docker.internal:11434` + `qwen3:8b`;
  sigiloso na nuvem em dev só com `LLM_ALLOW_CLOUD` e
  `LLM_DEV_CLOUD_OVERRIDE` (default false); supervisor em `supervisor.py`
  e não chama o LLM com `budget_truncated`. Miss-hunter continua desligado.
  Plano em [docs/plano-correcao-auditoria-2026-09-28.md](docs/plano-correcao-auditoria-2026-09-28.md).
- Cadeia free: gemini → groq → mistral → openrouter (+ Ollama `qwen3:8b`
  no host, p/ sigiloso). `.env` operacional: `ANALYSIS_BATCH_SIZE=5`,
  `ANALYSIS_MAX_LLM_CALLS=24`, `SUPERVISOR_REREVIEW_HIGH=true`,
  `MISS_HUNTER_ENABLED=false` (cap 10, fora do orçamento, pula com
  `budget_truncated`). Com TPM apertado (Groq 413), baixar o lote p/ 1–2.
- Qualidade medida: Groq golden R 0,56 / P 1,0; FTS piloto r@5 0,929;
  TR real golden v2 (`e2e/golden/real/tr_pabx.json`: 3 TPs humanos 16/09 +
  18 tripwires, 17 pendentes rejeitados 28/09 0A/17R contra o PDF
  09-ti-pabx-nuvem — truncado era quebra de linha, 4.3/4.9.1/DDR não se
  sustentam). Recall v1 0,25 (3/12) arquivado como validação do harness;
  re-medir pendente (Postgres piloto com zero análises em 28/09).
  ([docs/ops/recall-tr-real-2026-09.md](docs/ops/recall-tr-real-2026-09.md))
- Ciclo de anotação fechado (28/09): golden v2
  (3 TPs 16/09 não reabertos + 17 rejeitados com motivo na planilha);
  recomendação máquina 10A/7R superada e arquivada como histórico.
- Anotação acelerada (28/09): planilha fechada
  (`e2e/golden/real/anotacao_pabx_pendentes.md`, 0/17 com prova no PDF) +
  eleição dos próximos (`07-obra` × `10-monitoramento`,
  [README](e2e/golden/real/README.md)).
- Confiança: roda sem quebrar ALTA; precisão MÉDIA-ALTA; **recall o ponto
  vermelho**; free exige babysitting. Bom piloto **assistido**, não p/
  confiança cega.
- Jobs PABX de referência: `8cdafd60` (batch5, completed, nota 9.3),
  `f9648727` (parcial 186/257).
- Spike PNCP (28/09, `feat/fetch-pncp-trs`, commit `240b1bc`, sem merge):
  baixa TRs públicos da CODEBA sem token (`services/pncp/client.py` +
  `scripts/fetch_pncp_trs.py`, dry-run default, 6 testes mock); PDFs em
  `fixtures/trs-codeba/pendente/pncp/`
  ([docs/ops/fetch-pncp-trs.md](docs/ops/fetch-pncp-trs.md)).

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

- Humano: carimbo golden feito (0/17, 28/09); **Go do gate 14d** — buscar
  TRs no SEI nesta semana; re-medir recall v2 quando houver análise no
  Postgres (hoje zero); ligar miss-hunter e comparar; colar SEI em minuta
  de teste; chaves pagas só se a Fase 3 mandar (`ANTHROPIC_API_KEY` c/ teto,
  SiliconFlow/Z.ai/Cohere/NVIDIA, permissão HF); URLs oficiais TCU (sair da
  quarentena); visto jurídico da amostra.
- Código: teste ao vivo do batch 1–2 no reset da cota; upload-tr full
  happy-path (redirect ok, conclusão travou na cota 28/09); bumps
  `starlette`/`multipart`/`pdfminer` em branch própria; `AnthropicProvider`
  só se Fase 3 mandar.
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
