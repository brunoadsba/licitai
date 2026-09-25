# Auditoria Técnica — LicitAI (Projeto Piloto CODEBA)

**Data:** 25/09/2026
**Escopo:** `backend/` (FastAPI), `frontend/` (Next.js 14), `docker-compose.yml`, `db/`, `docs/ops/`, configs e segurança do piloto single-user
**Método:** leitura de arquitetura + amostragem de código + métricas estáticas + checagem OWASP/12-factor/SRE. Sem teste de penetração, sem carga.
**Padrão:** indústria — ISO 25010 (qualidade), OWASP ASVS L1/L2, 12-factor, SRE (SLO/saúde/prontidão)

---

## 1. Resumo executivo

Piloto **bem acima da média de MVP**: arquitetura limpa (API + worker + BFF + Postgres pgvector), segurança consciente (fail-closed para sigiloso, BFF sem token no browser, non-root, CSP, rate-limit), saúde operacional (`/livez`/`/readyz`/`/metrics`), migrações Alembic versionadas e documentação viva rara em piloto (`README`, `memory.md`, `docs/ops/` com 20+ runbooks).

**Nota de maturidade para produção (single-tenant piloto → produção interna): 7,2 / 10.**

O que impede produção plena hoje, em ordem:

1. **CI desligado** (`.github/workflows/ci.yml.disabled`) — sem gate automático, regressão entra em `main` sem barreira.
2. **Auth de piloto** (`API_TOKEN` compartilhado, sem identidade/auditoria por usuário) — OK para piloto, bloqueador para multiusuário/LGPD plena.
3. **Resíduos de desenvolvimento no Compose/host** (`.env` mínimo, `APP_ENV=development`, SQLite permitido, Swagger aberto em dev) — risco de subir staging/prod com perfil dev.
4. **Falta de enforce de qualidade** (ruff/eslint/typecheck/testes não rodam em gate; ruff nem instalado no `.venv`).
5. **Git sujo** no momento da auditoria (8 modificados + 4 untracked em `chat/`) — indica trabalho em voo sem branch/PR.

Nenhum secret hardcoded encontrado. Nenhum `bare except`, nenhum `print(`, zero `console.log`. Higiene de código boa.

---

## 2. Inventário medido (25/09/2026)

| Sinal | Valor |
|---|---|
| Backend `app/` | 169 arquivos `.py`, **19.541 LOC** |
| Maiores arquivos | `rag/loader.py` 339, `analyzer/evidence_gate.py` 324, `rag/semantic.py` 323, `analyzer/analysis_persistence.py` 315, `api/documents.py` 311 — todos < 400, nenhum monolito crítico |
| Testes backend | **69 arquivos** em `backend/tests/` |
| Frontend `src/` | **130 arquivos** `.ts/.tsx`, `strict:true`, `paths @/*` |
| TODO/FIXME/HACK | **37 ocorrências** |
| Supressões (`as any`, `ts-ignore`, `noqa`) | **21 ocorrências** |
| `except:` nu | 0 |
| `print(` backend | 0 |
| `console.log` frontend | 0 |
| Compose | 4 serviços (`db`, `backend`, `worker`, `frontend`), todos com `healthcheck`, rede única, volumes `pgdata`/`uploads` |
| Docs ops | 20+ arquivos em `docs/ops/` |
| Git (na auditoria) | `main` em `7846070`; 8 modificados + 4 novos não commitados, todos em `chat/` + `memory.md` + `smoke_readyz.sh` |

---

## 3. Pontos fortes (manter)

- **Separação API/worker:** `POST .../start` só enfileira (`jobs` no Postgres + `app/worker.py` com lease 900s + heartbeat). Sem Redis — decisão correta para piloto.
- **BFF correto:** `frontend/src/app/api/proxy/*` injeta `API_TOKEN` server-side; `NEXT_PUBLIC_API_TOKEN` inexistente. Rewrites legados isolados em `next.config.js`.
- **Fail-closed privacidade:** `NULL = sigiloso`, cloud bloqueada, 422 proposital sem Ollama. `config.py` com `model_validator` que quebra boot fora de `development` sem Postgres+token e sem `LLM_ALLOW_CLOUD=true`. Isso é padrão indústria.
- **Upload hardening:** allowlist extensão + magic bytes (`python-magic` + `libmagic1` no Dockerfile), UUID no disco fora do web root, `MAX_UPLOAD_SIZE_MB=50`.
- **Saúde SRE:** `/livez` (vivo), `/readyz` (DB + `schema_version` vs `expected_schema_version=20260924_004`), `/metrics` in-memory com proteção por token fora de dev.
- **Migrações:** Alembic `20260908_001…20260924_004`; `create_all` só em SQLite dev/teste.
- **Imagens:** backend `python:3.12-slim` + `tesseract-ocr-por` + usuário `licitai:10001`; frontend multi-stage `node:20-alpine` com `nextjs:1001` e `output:standalone`. Workers FastAPI = 1 com justificativa documentada (semáforo/rate in-process).
- **RAG honesto:** FTS Postgres (`unaccent`+`portuguese`+GIN) com fallback ILIKE, quarentena TCU sem URL oficial fora da busca padrão, `RetrievedChunk.id` persistido, grounding obrigatório no chat.

---

## 4. Achados e oportunidades

### 4.1 Arquitetura — P1

1. **TOCTOU parcialmente tratado, mas sem teste de concorrência visível.** `with_for_update()` em `start_analysis`/`start_comparacao` é correto; falta teste de duplo-start simultâneo.
2. **Rate-limit e semáforo in-process.** Documentado como single-user. Com `--workers 1` funciona; escalar horizontal quebra o limite. Migração futura: Redis/token-bucket ou gateway.
3. **N+1 corrigido em `list_comparacoes`**, mas sem política geral (ex.: `joinedload`/`selectinload` como default em listagens). Recomendar lint de queries em PRs grandes.
4. **Extensão SEI (`extension/`) fora do build/test.** Se é opcional, isolar em repo próprio ou versionar com manifesto + teste de sanitização.

### 4.2 Backend / Qualidade — P1/P2

1. **Ruff configurado, não executado.** `pyproject.toml` com `line-length 100` + `E4,E7,E9,F,I,B`, mas `ruff` não instalado no `.venv` → zero enforce. **Ajuste:** adicionar `ruff` a `requirements-dev.txt` + pre-commit + gate CI.
2. **37 TODOs + 21 supressões.** Volume aceitável para piloto, mas sem dono/prazo. **Ajuste:** converter em issues com `TODO(user, data)` ou limpar; auditar os 21 `noqa`/`any` um a um.
3. **Arquivos 300+ LOC concentrados em RAG/analyzer/api.** Não são defeito, mas são o teto. **Ajuste:** congelar em ~350 LOC; próxima feature em `loader.py`/`evidence_gate.py`/`documents.py` deve extrair módulo.
4. **`scripts/` com `per-file-ignores` amplo (`I,F401`).** 30+ scripts avulsos (ingest, backfill, migrate legado, benchmark). **Ajuste:** separar `scripts/ops/` vs `scripts/legacy/`; marcar legados `migrate_*` como deprecated em favor do Alembic.
5. **1× `except Exception` + `pass` (contagem via grep).** Localizar e logar; política: nunca silenciar sem `logger.warning` + métrica.
6. **Duplo suporte SQLite/Postgres.** Pragmático no piloto, mas FTS diverge (FTS5 vs `to_tsquery`) e `with_for_update()` é no-op no SQLite. **Ajuste:** CI deve rodar os dois; documentar diferenças conhecidas.

### 4.3 Frontend — P1/P2

1. **TS `strict:true` + zero `console.log` — bom.** Manter.
2. **ESLint mínimo** (`next/core-web-vitals` + 1 regra off). Sem `typescript-eslint` estrito, sem `import/order`, sem barreira de `any`. **Ajuste:** `npm run lint` + `tsc --noEmit` no CI; considerar `eslint --max-warnings 0`.
3. **CSP com `script-src 'unsafe-inline'`** — necessário ao App Router sem nonce, mas registrado como exceção técnica com plano de nonce por request. OK para piloto.
4. **`output:standalone` + `ARG BACKEND_URL` embutido no build** — correto, mas exige `--build` a cada mudança de UI (já documentado em `README`). Risco operacional: esquecer `--build` e testar UI velha. **Ajuste:** versionar build (`NEXT_BUILD_ID` ou label de imagem com sha).
5. **Polling com backoff + pausa em aba oculta (`lib/polling.ts`) — bom.** Faltam testes de polling/erro 429/503 visíveis no piloto.

### 4.4 Segurança (OWASP ASVS) — P0/P1

| Check | Estado |
|---|---|
| Sem secret hardcoded | ✅ (`config.py` só env; `.env` gitignored; `.dockerignore` exclui `.env`) |
| Token obrigatório com Postgres | ✅ (`_enforce_production_secrets`) |
| `compare_digest` no token | ✅ |
| CORS allowlist, `allow_credentials=False` | ✅ |
| CSP backend restritivo + frontend alinhado | ✅ com exceção `unsafe-inline` documentada |
| Rate-limit 600 req/min in-memory | ⚠️ OK piloto, insuficiente multi-instância |
| Validação upload (extensão+magic+UUID) | ✅ |
| Swagger só em dev | ✅ |
| PII scrub (`pii_scrub.py`) | ✅ existência; cobertura não auditada a fundo |
| SMTP sem default seguro verificado | ⚠️ `smtp_require_tls=True` por default — bom; validar timeout + credencial em vault |
| `.env` real com 354 bytes no host | ⚠️ não inspecionado por segurança; garantir `POSTGRES_PASSWORD` + `API_TOKEN` fortes e fora de backup git |
| Auth single-token | 🔴 **P0 para qualquer expansão:** sem identidade, sem RBAC, sem trilha por usuário, sem rotação automática |

**Ajustes necessários (segurança):**
- Rotação de `API_TOKEN`/`POSTGRES_PASSWORD`/chaves LLM pós-piloto (já previsto em `memory.md` como pendência do Bruno — formalizar data).
- `TRUST_PROXY` só `=1` atrás de proxy confiável; hoje o `_client_key` lê `X-Forwarded-For` apenas se opt-in — manter.
- Adicionar headers ausentes: `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`, `Strict-Transport-Security` (quando houver TLS).
- `/metrics` exposto via rewrite `/metrics` → backend; garantir que em prod exige token (já exige fora de dev — validar em staging).
- OCR em subprocesso com hard-timeout — bom; confirmar limite de CPU/memória no Compose para `worker` (evitar DoS via PDF bomba).

### 4.5 Dados / RAG / IA — P1

1. **Recall@5 0,929 FTS em 599 chunks — bom para piloto.** `pgvector` preenchido via JSON sem HNSW. **Ajuste:** antes de trocar dimensão/modelo de embedding, exigir eval `eval_corpus_real.py --check-baseline`; não reduzir dimensão sem medir recall (já documentado — manter como regra).
2. **Quarentena TCU correta**, mas com 3 peças em `quarantine-0B` e URLs pendentes (humano). Risco jurídico se sair da quarentena sem visto. Manter gate humano.
3. **`ANALYSIS_MAX_LLM_CALLS=24` + `ANALYSIS_CONCURRENCY=1` no Compose** — contenção de free-tier correta; documentar como teto de piloto, não de produção.
4. **Prompts com `<DOCUMENT_DATA>` + `llm_timeout 120s` + failover simétrico + circuit-breaker 429** — padrão bom. Faltam SLOs de custo/latência por análise (só `llm_usage` em log + `/metrics` in-memory).
5. **Ingestão sequencial obrigatória** (documentada). Faltam lock de ingestão para impedir paralelização acidental no mesmo banco.

### 4.6 Testes / CI-CD — **P0**

1. **CI desligado é o maior débito.** `ci.yml.disabled` + nota “não reabilitar sem pedido explícito”. Para padrão indústria, piloto pode ter CI leve sem deploy:
   - `pytest backend/tests -q` (SQLite via `conftest`)
   - `test_init_sql.py` (parser `pglast`)
   - `ruff check` + `tsc --noEmit` + `next lint` + `next build`
   - `eval --seed --check-baseline`
2. **Cobertura desconhecida.** 69 arquivos de teste é ótimo, mas sem relatório `coverage` + sem badge/gate. **Ajuste:** `pytest --cov=app --cov-fail-under=70` como piso inicial, subir após.
3. **E2E existe (`e2e/`, 17 testes API + Playwright live 4/4) mas fora do CI.** Reativar ao menos o `e2e_fast` (privacy 422) por PR.
4. **Golden set + FakeLLM (`precision ≥0,88/recall ≥0,80`) — excelente.** Manter como porta de qualidade de prompt/modelo.

### 4.7 Operação / Observabilidade — P1

1. **Compose exemplar para piloto** (healthchecks, `depends_on: service_healthy`, `restart:unless-stopped`, bind `127.0.0.1`). Falta: `logging` com rotação, `mem_limit`/`cpus` no worker, `restart` policy testada em kill.
2. **Backup (`backup.sh` + `promote_feedback.py`) sem drill calendarizado.** `docs/ops/restore-drill.md` existe — agendar e registrar evidência.
3. **Métricas in-memory perdem-se no restart.** OK piloto; produção exige Prometheus/OTel + dashboard + alerta em `readyz 503` e `job_queue_depth`.
4. **Frontend sem bind mount (intencional) vs backend com `:ro`** — assimetria documentada, mas causa “funciona na minha máquina” se dev esquecer `--build`. Versionar imagem resolve.
5. **`licitacao.db` + `uploads/` + `backups/` no host.** `.gitignore` cobre, mas validar que nenhum dump foi commitado (`git log --all -- backups/`).

---

## 5. Riscos priorizados

### P0 — resolver antes de qualquer expansão
- [ ] **Reativar CI mínimo** (pytest + ruff + tsc + lint + build + eval seed). Sem isso, auditoria futura não escala.
- [ ] **Definir teto de auth:** manter `API_TOKEN` só para piloto single-user com data de validade; qualquer multiusuário exige OIDC/RBAC + trilha por usuário (fora de escopo atual, mas com decisão registrada).
- [ ] **Commitar ou descartar o git sujo** (`chat/*`, `AssistantAnswer`, `chatAnswer.ts`, `answer_sanitize.py` + teste). Auditoria com árvore suja não é reprodutível.
- [ ] **Rotação de secrets pós-piloto** + comprovação (sem expor valores).

### P1 — 30 dias
- [ ] Ruff + pre-commit + `tsc --noEmit` + `next lint` em gate.
- [ ] `coverage` com piso 70% e relatório por PR.
- [ ] Teste de concorrência `start_analysis` duplo + teste `readyz` mismatch.
- [ ] `SECURITY_HEADERS` backend × frontend unificados em um módulo/fonte única (hoje duplicados em `security.py` e `next.config.js`).
- [ ] HSTS + `Cross-Origin-*` quando houver TLS; validar `/metrics` com token em staging.
- [ ] `mem_limit`/quotas no `worker`; lock de ingestão.
- [ ] Versionar imagem frontend com sha; smoke `up.sh` validando versão.

### P2 — 60/90 dias
- [ ] Quebrar arquivos 300+ LOC sob demanda; tipar `scripts/legacy` como deprecated.
- [ ] Zerar/issue-izar 37 TODOs; revisar 21 supressões.
- [ ] OTel/Prometheus + alertas (`readyz`, `job_queue_depth`, `llm_errors`, `analysis_duration_avg`).
- [ ] Avaliar Redis só quando sair de single-instância (rate-limit/lock distribuído).
- [ ] Separar `extension/` ou adicionar teste de sanitização no CI.

---

## 6. Plano de ação 30/60/90

**30 dias (higiene + portas):** CI mínimo ligado; ruff+tsc+lint verdes; coverage piso; git limpo; rotação de secrets calendarizada; teste duplo-start; headers unificados.

**60 dias (confiabilidade):** backup drill evidenciado; quotas de container; lock ingestão; eval de recall como gate de mudança de embedding; dashboard mínimo (mesmo que log + `/metrics` raspado).

**90 dias (preparar produção):** decisão formal auth (manter piloto vs OIDC); trilha de auditoria por ator; SLOs escritos (`docs/ops/slos.md` já existe — publicar metas: disponibilidade, p95 análise, recall@5 piso); separar extensão; plano K8s só se necessário (hoje fora de escopo corretamente).

---

## 7. Veredito

**Aprovar piloto com ressalvas.** Código honesto, seguro para o escopo single-user e muito bem documentado. Para virar produção interna, o caminho é curto e conhecido: **CI + qualidade com gate + decisão de auth + observabilidade persistente**. Nada aqui exige rewrite; tudo é incremental — que é exatamente o que se espera de um piloto bem conduzido.

---

## A. Comandos de verificação usados

```bash
find backend/app -name "*.py" | wc -l
find backend/app -name "*.py" -exec wc -l {} + | sort -rn | head
ls backend/tests/*.py | wc -l
find frontend/src -name "*.ts" -o -name "*.tsx" | wc -l
grep -rni "TODO|FIXME|XXX|HACK" backend/app frontend/src | wc -l
grep -rn "as any|ts-ignore|noqa" backend/app frontend/src | wc -l
git log --oneline -8; git status --short
ls -l .github/workflows/; cat backend/.dockerignore; cat frontend/.eslintrc.json
```
