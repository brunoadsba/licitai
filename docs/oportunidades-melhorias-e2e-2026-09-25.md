# Oportunidades de Melhoria — LicitAI (Auditoria + E2E 25/09/2026)

**Plano de implementação:** [docs/ops/plano-30-60-90.md](ops/plano-30-60-90.md).

**Base:** `docs/auditoria-piloto-2026-09-25.md` + auditoria E2E desta sessão (branch `feat/copiloto-ux`, HEAD `7846070`, 4 containers healthy, smoke OK).
**E2E executado:** Camada 0 smoke + BFF OK · `e2e_fast` 11 passed (com token) · precision/chat 37 passed + privacy 6 passed · Playwright smoke 3 passed/1 skipped.
**Nota atual:** 7,2/10 — piloto aprovado com ressalvas. Nada exige rewrite.

Regra do piloto (não quebrar): sem segundo LLM no analyzer, sem tirar TCU da quarentena, sem religar CI sem pedido, sem misturar stash `wip classificacao-padrao-publico`.

---

## 1. P0 — bloqueiam expansão (fazer primeiro)

### 1.1 CI mínimo desliga regressão silenciosa
**Achado:** `.github/workflows/ci.yml.disabled`; qualidade só manual. Ruff nem instalado no `.venv`.
**Oportunidade:** gate leve por PR sem deploy: pytest SQLite + `test_init_sql.py` + `ruff check` + `tsc --noEmit` + `next lint` + `next build` + eval seed `--check-baseline`.
**Aceite:** PR com teste quebrado ou `ruff` vermelho não mergeia; `e2e_fast` verde inclui 422 de classificação.

### 1.2 Árvore suja não reprodutível
**Achado:** 11 modificados + 6 untracked (`chat/*`, `AssistantAnswer`, `chatAnswer.ts`, `answer_sanitize.py` + teste, `smoke_readyz.sh`, `.cursor/`, `contexto-auditoria.sh`).
**Oportunidade:** commitar por escopo (F2 copiloto / F3 smoke-retry / docs) ou descartar; exigir `git status` limpo antes de qualquer re-run ouro.
**Aceite:** `git status --short` vazio (fora `docs/auditoria*`) + tag da sessão E2E.

### 1.3 Auth de piloto tem teto
**Achado:** `API_TOKEN` compartilhado, sem identidade/RBAC/trilha por usuário. `compare_digest` + Postgres-exige-token estão corretos para single-user.
**Oportunidade:** formalizar: piloto = token operacional com validade + donos; qualquer multiusuário exige OIDC/RBAC + auditoria por ator (decisão registrada, fora do escopo atual).
**Aceite:** documento de 1 página com validade do token + plano de rotação.

### 1.4 Rotação de secrets pós-piloto
**Achado:** `.env` real no host (43 chars de token), `POSTGRES_PASSWORD`/chaves LLM sem evidência de rotação.
**Oportunidade:** calendarizar rotação + comprovação sem expor valores; validar que `backups/` nunca entra no git.
**Aceite:** checklist assinado + `git log --all -- backups/` limpo.

---

## 2. P1 — 30 dias (maior retorno/esforço)

### 2.1 Enforce de qualidade (ruff + tsc + lint)
- Ruff `pyproject` existe (`E4,E7,E9,F,I,B`, `line-length 100`) mas sem execução. Adicionar a `requirements-dev.txt` + pre-commit + CI. Auditar os 21 `noqa`/`any`/`ts-ignore` um a um.
- Frontend: `tsc --noEmit` + `next lint --max-warnings 0` no gate; avaliar `typescript-eslint` + `import/order`.
- Congelar arquivos 300+ LOC (`rag/loader.py` 339, `evidence_gate.py` 324, `rag/semantic.py` 323, `documents.py` 311): próxima feature extrai módulo.

### 2.2 Cobertura com piso
- 69 arquivos de teste é ótimo, mas sem número oficial. Subir `pytest --cov=app --cov-fail-under=70`, depois 80. Manter golden FakeLLM (precision ≥0,88/recall ≥0,80) como porta de prompt/modelo.

### 2.3 F1 — fechar o loop ouro (humano + máquina)
- **Estado:** fix em `main` `7846070` (G2/G4 + `document_inventory.py` + instrução 4 `prompts.py:149`); precision verde. Falta re-run ouro.
- **Oportunidade:** Bruno reenviar `fixtures/trs-codeba/piloto-unico/09-ti-pabx-nuvem.pdf` em econômico, conferir item 1.1 sem `[prazo]/[quantidade]`/omissão Art.6(a) quando o fato está em 1.4/4.3.2/11.5.
- **Aceite:** print/evidência do 1.1 + `test_analysis_precision.py` verde.

### 2.4 F2 — merge do copiloto
- **Estado:** só branch/working tree — Dialog `w-[min(96vw,1100px)]` (`ChatCopilot.tsx:54`), `answer_sanitize.py` (UUID/`source_id`/`agent:failed`/rodapé parecer), teste verde. Imagem 09:17 já inclui (arquivos 09:13). Não está em `main`.
- **Oportunidade:** merge dedicado `feat/copiloto-ux` (sem F5), com teste manual: Perguntar abre centro quase-tela-cheia, resposta sem UUID/`estrutural:failed`/rodapé de IDs.
- **Aceite:** merge + smoke Playwright + evidência de tela.

### 2.5 F3 — commitar o retry do smoke
- **Estado:** `smoke_readyz.sh` no disco já tem retry 10×2s; smoke agora 200 em tudo; BFF 200. Era corrida, não regressão.
- **Oportunidade:** commitar o retry + documentar `up.sh --build` exige espera do Next.
- **Aceite:** `up.sh --build` seguido de smoke verde de primeira.

### 2.6 E2E à prova de erro de invocação
- **Achado:** `e2e_fast` sem token falha 9×401; com `source .env` passa 11/11. `docs/ops/e2e-full.md` cita token mas o comando copiável omite.
- **Oportunidade:** prefixar todos os comandos E2E com `set -a; source .env; set +a` + fail-fast que aborta se `API_TOKEN` vazio.
- **Aceite:** copiar-colar da doc passa de primeira.

### 2.7 Segurança e operação
- Unificar `SECURITY_HEADERS` (hoje duplicados em `security.py` e `next.config.js`); adicionar HSTS + `Cross-Origin-*` quando houver TLS; validar `/metrics` com token em staging.
- Teste de duplo-`start_analysis` (TOCTOU `with_for_update`); teste `readyz` mismatch de `schema_version`.
- `mem_limit`/`cpus` no `worker` (anti PDF-bomba); lock de ingestão (sequencial obrigatório); `NEXT_BUILD_ID`/label sha na imagem frontend (evita testar UI velha sem `--build`).
- Backup drill calendarizado com evidência (`restore-drill.md` existe).

---

## 3. P2 — 60/90 dias (endurecer para produção interna)

- OTel/Prometheus + alertas (`readyz 503`, `job_queue_depth`, `llm_errors`, `analysis_duration_avg`); métricas hoje in-memory zeram no restart.
- Zerar/issue-izar 37 TODOs; separar `scripts/ops/` vs `scripts/legacy/` (Alembic é o caminho, `migrate_*` deprecated).
- Política N+1 padrão (`selectinload` em listagens); lint de queries em PRs grandes.
- `extension/` SEI: repo próprio ou teste de sanitização no CI.
- Redis só ao sair de single-instância (rate-limit/lock distribuído). K8s/fine-tune/OIDC seguem fora até decisão.
- SLOs publicados (`slos.md` existe): disponibilidade, p95 análise, recall@5 piso 0,90, custo/teto LLM.

---

## 4. Plano 30/60/90

**30 dias:** CI mínimo + ruff/tsc/lint verdes; coverage piso 70; git limpo + tag E2E; F3 commitado; F2 mergeado; F1 re-run ouro pelo Bruno; comandos E2E com token; rotação de secrets datada; duplo-start + readyz-mismatch testados; headers unificados.
**60 dias:** backup drill evidenciado; quotas worker; lock ingestão; recall@5 como gate de embedding; dashboard mínimo raspando `/metrics`.
**90 dias:** decisão auth (piloto vs OIDC); trilha por ator; SLOs publicados; extensão isolada; avaliar K8s só se necessário.

---

## 5. Métricas da sessão (evidência)

```text
backend/app: 169 .py, 19.541 LOC, maiores 339/324/323/315/311
backend/tests: 69 arquivos · frontend/src: 130 .ts/.tsx, strict:true
TODOs: 37 · supressões: 21 · bare except: 0 · print(: 0 · console.log: 0
smoke_readyz: 6×200 + 4 healthy · smoke_e2e_compose: BFF 4×200 OK
e2e_fast (com token): 11 passed · precision/chat: 37 passed · privacy unit: 6 passed
playwright smoke.spec.ts: 3 passed, 1 skipped
git: feat/copiloto-ux @7846070 (=main), 11M+6U, stash wip classificacao-padrao-publico
imagens licitai-* 09:17 BRT incluem working tree 09:13 BRT (F2 no runtime, fora de main)
```

## 6. Arquivos-fonte desta análise

- `docs/auditoria-piloto-2026-09-25.md` (auditoria geral)
- `.cursor/contexts/auditoria-e2e-falhas.md` (protocolo F1–F5)
- `docs/ops/e2e-full.md`, `memory.md`, `scripts/smoke_readyz.sh`, `scripts/smoke_e2e_compose.sh`
- `backend/app/services/analyzer/evidence_gate.py`, `document_inventory.py`, `prompts.py:149`
- `frontend/src/components/chat/ChatCopilot.tsx:54`, `backend/app/services/chat/answer_sanitize.py`
