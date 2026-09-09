# Deploy — práticas de confiabilidade

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
- Smoke: `./scripts/smoke_readyz.sh` depois `docker compose up -d` (valida `/livez`, `/readyz`, `/api/docs`, frontend `/readyz` e health dos containers).
- Frontend: build arg `BACKEND_URL=http://backend:8000` obrigatório (rewrites do Next são embutidos no build).
- Schema: Alembic head `20260908_003` (ou `scripts/apply_reliability_schema.sql` em Postgres já provisionado).
- LLM defaults: Groq `openai/gpt-oss-20b`, Gemini `gemini-flash-latest`; `ANALYSIS_CONCURRENCY=1` no free tier.

## Checklist pré-promote

- [ ] Digest imutável publicado
- [ ] Trivy sem CRITICAL aberto
- [ ] Migrações Alembic aplicadas em staging
- [ ] Worker e API na mesma versão (enqueue-only na API)
- [ ] Backup recente + restore drill no ciclo
- [ ] `/livez` e `/readyz` OK; CI permanece opcional (`ci.yml.disabled`)
