# Plano de Correção — Auditoria Backend 15/09/2026

> Origem: auditoria profunda backend (P0+P1+P2). Branch base: `main` (`87fdd33`).
> Invariante piloto: single-user, 1 worker. Não abrir multi-worker até Fase 1 pronta.
> CI segue desabilitado. Validar com `pytest backend/tests -q` + E2E 17/17 ao fim de cada fase.

## Objetivo

Eliminar 4 P0 + 7 P1 + 6 P2 sem regressão: failover correto, sem duplo processamento, upload sem OOM, parse sem thread órfã, rate-limit e métricas seguros, status honesto.

## Fase 0 — Trava de segurança (30 min, antes de tudo)

1. Criar branch `fix/backend-auditoria-15-09` a partir de `main`.
2. Congelar `ANALYSIS_MAX_LLM_CALLS=24`, `ANALYSIS_CONCURRENCY=1`, 1 worker no Compose.
3. Rodar baseline: `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q` → anotar verdes (esperado 258).
4. Critério de saída: baseline verde anotado no PR/commit.

## Fase 1 — P0 (bloqueantes, ~1 dia)

### 1.1 Failover `is_last_provider` errado
- Arquivo: `backend/app/services/llm/provider.py:118-186`
- Problema: `position == len(self._providers)-1` usa total, não lista filtrada por cooldown → mensagem e lógica de "último" erradas.
- Correção:
  ```python
  ordered = self._ordered_providers()
  for position, (index, provider) in enumerate(ordered):
      is_last_provider = position == len(ordered) - 1
  ```
- Teste novo `backend/tests/test_llm_failover_last.py`:
  - 2 providers, 1 em cooldown forçado → `generate` usa o livre e loga "Nenhum fallback restante" só quando real.
  - Todos em cooldown → tenta mesmo assim (comportamento atual preservado).
- Aceite: teste verde + `test_llm_resilience.py` + `test_llm_timeout.py` verdes.

### 1.2 Claim SQLite sem lock (duplo processamento)
- Arquivos: `backend/app/services/jobs/queue.py:50-118`, `backend/app/worker.py`
- Correção mínima (sem migração):
  - `claim`: trocar `SELECT+UPDATE` por `UPDATE ... WHERE status='pending' RETURNING` no Postgres; no SQLite fazer `UPDATE jobs SET status='running', ... WHERE id=(SELECT id ... WHERE status='pending' LIMIT 1) AND status='pending'` e checar `rowcount==1`, senão retornar None.
  - `claim_by_id`: mesmo padrão com `WHERE id=:id AND status='pending'`.
  - Documentar invariante em `queue.py` docstring: "só 1 worker suportado até lock distribuído".
- Teste `backend/tests/test_jobs_race.py`:
  - 2 `claim` concorrentes (asyncio.gather) no SQLite → só 1 retorna job, outro None.
  - `claim_by_id` duplo → idem.
- Aceite: sem duplicata, suíte jobs verde.

### 1.3 Upload em RAM antes do limite
- Arquivos: `backend/app/api/documents.py` (endpoint upload), `app/services/upload_service.py:31-43`, `app/utils/file_validation.py:90-106`
- Correção:
  - No endpoint, ler `Content-Length` / `UploadFile.size` antes de `await file.read()`; se > `max_upload_size_bytes` → 413 imediato.
  - Ler em chunks com teto (`read(MAX+1)` e abortar se passar).
  - `magic.from_buffer` manter 8KB mas mapear `application/zip`/`octet-stream` para DOCX/ODT via checagem de assinatura ZIP + `[Content_Types].xml`/`content.xml` antes de rejeitar (evita falso 400 visto no fixture).
- Teste `backend/tests/test_upload_limits.py`:
  - Arquivo > limite → 413 sem alocar corpo completo (mock size).
  - DOCX mínimo válido → aceito mesmo se libmagic disser `application/zip`.
- Aceite: E2E upload verde, sem OOM em smoke 60MB.

### 1.4 Parse timeout com thread órfã
- Arquivos: `backend/app/services/parser/__init__.py:30-56`, `ocr_subprocess.py`, `pdf_parser.py`
- Correção piloto (sem IPC complexo):
  - Fila `parse` com `max_concurrent=1` (semáforo global parse) + `PARSE_TIMEOUT_SECONDS` via env.
  - Se timeout, marcar `document.status=error` com msg "timeout, reenvie" e logar thread órfã (id + arquivo).
  - Médio prazo (anotar, não fazer agora): OCR PDF também em subprocesso com kill, igual `_extract_with_ocr` já faz.
- Teste: timeout simulado (mock `parse_pdf` sleep 5s, timeout 1s) → 408/timeout + status error, sem travar loop.
- Aceite: upload concorrente não congela `/health`.

## Fase 2 — P1 (~1-2 dias)

### 2.1 `_handle_orphans` com corrida
- Arquivo: `backend/app/worker.py:47-125`
- Correção: rodar `reclaim_expired` + `commit` primeiro; depois requeue `pending` com `claim_by_id` atômico em vez de `enqueue` cego; `running` só vira `error` se `lease_until` expirado ou ausente há >2x lease.
- Teste: boot duplo simulado → só 1 job re-enfileirado.

### 2.2 Rate-limit leak + IP
- Arquivo: `backend/app/utils/security.py:73-111`
- Correção: `OrderedDict`/TTL com evicção (max 5k IPs), limpeza de IPs vazios; ler `X-Forwarded-For` quando `TRUST_PROXY=1`, senão `client.host`; adicionar teste de 601ª req → 429 + `Retry-After`.
- Aceite: sem crescimento ilimitado em soak 10k req simuladas.

### 2.3 `UPLOAD_DIR.mkdir` no import
- Arquivo: `backend/app/utils/file_validation.py:24-25`
- Correção: remover `mkdir` top-level; criar em `lifespan` do `main.py` + em `salvar_arquivo_upload` (já tem). Teste: importar módulo com `UPLOAD_DIR` read-only não cria pasta.

### 2.4 Status documento honesto
- Arquivo: `backend/app/services/analyzer/engine.py:407-430`
- Correção: se `completed_with_errors` → `document.status='completed'` só se ≥1 item ok? Proposta: manter `document.status='completed'` mas adicionar `document.error_message` / flag, ou novo status `completed_with_errors` no CHECK (requer Alembic `20260915_004`). Escolher 1ª opção sem migração no MVP: setar `document.error_message` com resumo + UI mostra banner (já mostra para análise).
- Teste: análise parcial → doc com aviso visível na API.

### 2.5 `total_items` vs `work_items`
- Arquivo: `engine.py:169,221`
- Correção: preservar `total_items=len(document.items)` original; adicionar `analyzed_total=len(work_items)` no `run_snapshot`. Ajustar scoring/report para usar `work_items`.
- Teste: TR com sumário → `total` original ≠ `analyzed`, relatório coerente.

### 2.6 `/metrics` e `/api/docs` abertos
- Arquivo: `backend/app/main.py`
- Correção: gate `metrics` por `API_TOKEN` quando `APP_ENV!=development`; `docs_url=None` em staging/prod ou atrás de token. Manter `/livez`/`/readyz` abertos para Compose.
- Teste: staging sem token → `/metrics` 401, `/readyz` 200.

### 2.7 `threading.Lock` em async
- Arquivo: `backend/app/utils/metrics.py`
- Correção: trocar por `collections.Counter` sem lock (GIL) ou `asyncio.Lock` com path sync preservado. Simples: remover lock, usar `time.monotonic` para uptime.
- Teste: 1k `inc` concorrentes → contagem exata.

## Fase 3 — P2 hardening (meio dia)

- PDF: preservar causa raiz dos 2 parsers em `error_message` (`pdf_parser.py:43-50`).
- OCR parcial: se OCR falhar, anexar `warning` no documento em vez de silencioso.
- ODT: validar `namelist` (recusar `..`, links), limitar nº entries (ex: 5k) + total uncompressed (ex: 200MB) além dos 50MB do `content.xml`.
- Dedup: logar `deduplicated dropped agent_origin` em debug para explicar rejeição 90%.
- SMTP: documentar TLS obrigatório + teste porta 25 recusada (já existe, só garantir).
- `get_upload_path`: trocar `startswith` por `Path.is_relative_to()`.

## Verificação final por fase

- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q`
- `E2E_BASE_URL=http://127.0.0.1:8000 PYTHONPATH=backend pytest e2e/tests -q` (17/17)
- `./scripts/smoke_readyz.sh` + `./scripts/up.sh --e2e` camada 0
- `tsc --noEmit` no frontend se mexer em contrato (Fase 2.4/2.5)

## Riscos e não-escopo

- Não implementar multi-worker, Redis, K8s, fine-tune.
- Migração Alembic só se optar por status novo em 2.4; preferir sem migração.
- Não reabilitar CI sem pedido.
- Secrets e anonimização Emergência continuam manuais (fora deste plano).

## Ordem de execução

Fase 0 → 1.1 → 1.2 → 1.3 → 1.4 → 2.1 → 2.2 → 2.3 → 2.4+2.5 juntos → 2.6+2.7 juntos → Fase 3 → E2E full + atualizar `memory.md` §5/§7.
