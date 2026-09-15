# Plano — Incrementos Seguros 15/09/2026 (pós-auditoria, sem comprometer piloto)

> Branch: `feat/incrementos-seguros-15-09` (base `main` `d50841f`).
> Invariantes piloto: single-user, 1 worker, dado CODEBA sigiloso fica local, CI desabilitado, gate 14d até 28/09 com métricas comparáveis.
> Origem: análise DeskcommCRM + vibecoding (context7/gitingest/MCP/models). Só entra o que é reversível, sem migração e sem cloud com TR real.

## Objetivo

Trazer quick wins de confiabilidade/ops/dev sem mudar comportamento do job único: idempotência API, correlação de request, scrub PII, teto LLM por análise, ops com backup, MCP dev-only, hardening frontend dev-only.

## Fase 0 — Trava (30 min, antes de tudo)

1. Branch `feat/incrementos-seguros-15-09` a partir de `main` (feito).
2. Congelar `ANALYSIS_MAX_LLM_CALLS=24`, `ANALYSIS_CONCURRENCY=1`, 1 worker no Compose.
3. Baseline: `PYTHONPATH=backend python3 -m pytest backend/tests -q` → anotar (esperado 261).
4. Critério de saída: baseline verde anotado.

## Fase 1 — P0 seguro (confiabilidade, ~1 dia)

### 1.1 Idempotency-Key em POSTs `start_*`
- Arquivos: `backend/app/api/analysis.py`, `backend/app/api/comparison.py` (endpoints `start`), novo `backend/app/utils/idempotency.py`, `backend/tests/test_idempotency.py`.
- Padrão Deskcomm `lib/api/idempotency.ts` adaptado: header `Idempotency-Key` opcional; mesma key + mesmo corpo → retorna job existente (sem novo `enqueue`); key diferente → novo job. Sem migração (cache in-memory TTL 24h, max 5k keys com evicção).
- Aceite: duplo `start_analysis` com mesma key → 1 job; teste verde + suíte jobs verde.

### 1.2 `X-Request-Id` correlacionado ao audit/log
- Arquivos: `backend/app/main.py` (`RequestIdMiddleware` já injeta), `backend/app/utils/logging_config.py`, pontos de mutação (`analysis.py`, `comparison.py`, `documents.py`).
- Correção: propagar `request_id` no log JSON + campo `request_id` no retorno de mutações; nada de PII no log.
- Aceite: `POST start` retorna `request_id` igual ao header/log; grep sem CPF/e-mail no log.

### 1.3 Scrub PII antes de qualquer observabilidade externa
- Arquivos: `backend/app/utils/logging_config.py`, novo `backend/app/utils/pii_scrub.py`, `backend/tests/test_pii_scrub.py`.
- Padrão Deskcomm Sentry `beforeSend`: máscara CPF/e-mail/telefone + headers `Authorization/X-API-Token` em logs/exceções. Sentry em si segue **OFF por default** (`SENTRY_DSN` vazio = no-op); só liga com scrub ativo + dado fake.
- Aceite: teste com TR sintético contendo CPF/e-mail → saída mascarada; sem DSN nada sai do host.

### 1.4 Teto LLM por análise + modelo por parte
- Arquivos: `backend/app/config.py`, `backend/app/services/analyzer/engine.py`, `backend/app/services/llm/provider.py`.
- Evoluir `ANALYSIS_MAX_LLM_CALLS=24` (teto tosco) para teto por análise + `LLM_MODEL_JURIDICO/ESTRUTURAL` (forte) vs `LLM_MODEL_REDACAO` (leve); sem trocar defaults do piloto. Só config via env.
- Aceite: análise com teto 5 aborta com `completed_with_errors` + msg honesta; teste config verde.

## Fase 2 — P1 seguro (ops + dev, ~1 dia)

### 2.1 `update.sh` com backup + healthcheck (só ops local)
- Arquivos: `scripts/update.sh` (novo), `scripts/backup.sh` existente, `scripts/smoke_readyz.sh`, `docs/ops/deploy.md`.
- Padrão Deskcomm `update.sh`: (1) checa versão, (2) backup banco antes, (3) aplica código, (4) Alembic upgrade (só se head mudou), (5) smoke. Rollback = `restore.sh` manual. Nunca apaga `pgdata`.
- Aceite: dry-run documentado; `update.sh --help` explica; sem auto-update em prod.

### 2.2 MCP dev-only (Postgres RO + GitHub + browser)
- Arquivos: `.opencode/` ou docs `docs/ops/mcp-dev.md` (só config local, sem segredo no repo).
- Smithery: Postgres read-only p/ diagnóstico, GitHub p/ PR/issues, Playwright p/ QA visual. Nunca em prod; DSNs via env local.
- Aceite: doc com 3 MCPs + exemplo de uso; nenhum segredo commitado.

### 2.3 Frontend hardening sem mudar fluxo
- Arquivos: `frontend/src/app/403.tsx`, `503.tsx`, `frontend/src/components/ui/` (skeletons P0), `frontend/e2e/` + `axe-core` dev-only.
- Boundaries + páginas 403/503 PT-BR, skeletons em listas, axe no `playwright` dev. Sem mudar funil Enviar→Revisar→SEI.
- Aceite: `tsc --noEmit` limpo; axe sem violação crítica em `/upload` e `/analysis/[id]`; QA 375/768/1280 sem overflow.

### 2.4 Workflow context7/gitingest documentado
- Arquivo: `docs/ops/vibecoding.md` (novo, 1 página).
- Regra: antes de usar lib nova → context7 doc oficial; antes de copiar repo → gitingest blob; decisão de modelo via `models.dev`/`artificialanalysis` (janela + custo free tier).
- Aceite: doc curto com 3 comandos exemplo; sem código.

## Fase 3 — P2 / pós-gate (não fazer no gate)

- Flywheel UI (Evolução + Propostas com gate humano sobre `promote_feedback.py → golden`) — só após volume de thumbs-down.
- MCP expondo `sei-pack/corrected-html/chat` p/ extensão SEI.
- `event_log` + `unique(org,external_id)` p/ workers quando sair de 1 worker.
- `models.dev` reavaliação de modelo local (`hermes3`/`qwen3`) + `epoch.ai` decisão fine-tune (bloqueado até dataset).

## Verificação por fase

- `PYTHONPATH=backend python3 -m pytest backend/tests -q` (manter 261+ novos).
- `E2E_BASE_URL=http://127.0.0.1:8000 PYTHONPATH=backend:e2e/tests python3 -m pytest e2e/tests -q -m "e2e_fast"` (7/7) + live sob cota.
- `./scripts/smoke_readyz.sh` + `tsc --noEmit` se tocar frontend.
- `git diff --stat` revisado; sem segredo (`grep -ri "API_KEY\|PASSWORD" --include="*.py" backend/app | head` vazio fora de `config.py`).

## Riscos e não-escopo

- Não: multi-tenant/RLS/RBAC, K8s, Redis, fine-tune/ML, reabilitar CI, cloud com TR real (sigiloso), free-tier com dado CODEBA, migração Alembic nova (prefer sem migração), multi-worker.
- Sentry/cloud só com dado fake + scrub + opt-in explícito.
- Qualquer mudança que invalide métricas do gate (rejeição 90%, `completed_with_errors`, Art.6) → mover para pós-gate.

## Ordem de execução

Fase 0 → 1.1 → 1.2 → 1.3 → 1.4 → 2.1 → 2.2 → 2.3 → 2.4 → E2E full + `memory.md` §5/§8.
