# Deploy — práticas de confiabilidade

Piloto single-user (backup/alertas/secrets): ver [piloto.md](piloto.md).

## Imagem imutável

1. Build com tag por digest (não só `latest`):
   ```bash
   docker build -t licitai-api:git-$(git rev-parse --short HEAD) ./backend
   docker push … && docker inspect --format='{{index .RepoDigests 0}}' …
   ```
2. No Compose/orquestrador, pinne o digest (`image@sha256:…`).
3. Promova o mesmo digest de staging → produção (sem rebuild).

## Non-root

- Dockerfile do backend deve rodar como usuário não-root (`USER app` / uid ≥ 1000).
- Uploads e DB volumes com ownership compatível; sem `chmod 777`.

## SBOM e Trivy

```bash
# SBOM (exemplo syft)
syft licitai-api@sha256:DIGEST -o spdx-json > sbom.spdx.json

# Vulnerabilidades
trivy image --severity HIGH,CRITICAL licitai-api@sha256:DIGEST
```

Bloquear promote se CRITICAL sem mitigação documentada.

## Rollback

1. Mantenha o digest anterior anotado no runbook.
2. Reaponte o serviço para o digest anterior (sem migrate down agressivo).
3. Se a migração Alembic for incompatível, restaure backup (`restore-drill.md`) antes do digest antigo.
4. Valide `/livez`, `/readyz`, smoke upload→análise.

## Runtime local / Compose

- Serviços: `db`, `backend` (API), **`worker`** (processa `jobs`), `frontend` (BFF injeta `API_TOKEN`).
- Sem o `worker`, `POST .../start` só enfileira — análise/comparação não avançam.
- Subir / parar (atalhos; frontend sem bind mount — mudanças de UI exigem `--build`):

```bash
./scripts/up.sh              # unset env sujo + compose up -d + smoke_readyz
./scripts/up.sh --build      # após mudança de UI/imagem
./scripts/up.sh --e2e        # + smoke_e2e_compose (readyz + BFF /api/proxy)
./scripts/down.sh            # compose down; NÃO apaga pgdata
```

Equivalente manual:

```bash
unset POSTGRES_PASSWORD DATABASE_URL
docker compose up -d --build
./scripts/smoke_readyz.sh
# ou: ./scripts/smoke_e2e_compose.sh
```

- Frontend: build arg `BACKEND_URL=http://backend:8000` obrigatório (rewrites do Next são embutidos no build).
- Schema: Alembic head `20260908_003` (ou `scripts/apply_reliability_schema.sql` em Postgres já provisionado).
- LLM defaults: Groq `openai/gpt-oss-20b`, Gemini `gemini-flash-latest`; `ANALYSIS_CONCURRENCY=1` no free tier.
- No Compose, `DATABASE_URL` do backend/worker é **montado** como  
  `postgresql+asyncpg://sei_user:${POSTGRES_PASSWORD}@db:5432/...`  
  (não herdar `DATABASE_URL` do host).

## Problemas comuns (Compose / Postgres)

### `sei-backend` unhealthy + `password authentication failed for user "sei_user"`

**Sintoma:** `/readyz` retorna 503 `database: error`; worker/frontend não sobem por dependência.

**Causas frequentes (WSL/Windows):**

1. Variável `POSTGRES_PASSWORD` **exportada no shell** sobrescreve o `.env` no Compose. Se veio de cópia Windows, pode trazer `\r` (CRLF) — a senha fica 1 byte a mais e a autenticação falha.
2. Volume `pgdata` foi criado com **outra** senha; mudar só o `.env` **não** altera a senha já gravada no Postgres.

**Correção (sem apagar dados):**

```bash
# 1) .env em LF (sem CR)
#    (editar no editor com LF, ou normalizar o arquivo)

# 2) Não usar override do shell
unset POSTGRES_PASSWORD DATABASE_URL

# 3) Alinhar a senha do role à do .env atual (socket local costuma usar trust)
#    Substitua SEM_COLAR_A_SENHA_NO_CHAT — use a do .env:
docker exec sei-db psql -U sei_user -d sei_analise \
  -c "ALTER USER sei_user WITH PASSWORD 'SUA_SENHA_DO_ENV';"

# 4) Recriar API com env limpo
docker compose up -d --force-recreate --no-deps backend
docker compose up -d --no-deps worker frontend
./scripts/smoke_e2e_compose.sh
```

**Evitar:** `docker compose down -v` apaga o volume `pgdata` (dados locais). Só use se for reset deliberado.

**Prevenção:** preferir `./scripts/up.sh` (já faz `unset`); manter `.env` em LF no WSL. Se subir na mão: `unset POSTGRES_PASSWORD DATABASE_URL` antes do compose.

## Checklist pré-promote

- [ ] Digest imutável publicado
- [ ] Trivy sem CRITICAL aberto
- [ ] Migrações Alembic aplicadas em staging
- [ ] Worker e API na mesma versão (enqueue-only na API)
- [ ] Backup recente + restore drill no ciclo
- [ ] `/livez` e `/readyz` OK; CI permanece opcional (`ci.yml.disabled`)
