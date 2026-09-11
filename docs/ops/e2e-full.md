# E2E full — LicitAI

Runbook das três camadas. Branch de implementação: `feat/e2e-full`.

## Pré-requisitos

```bash
unset POSTGRES_PASSWORD DATABASE_URL   # WSL: evita senha com \r do shell
docker compose up -d --build
# stack healthy: db, backend, worker, frontend
```

Se `sei-backend` ficar `unhealthy` com erro de senha `sei_user`, ver [deploy.md — Problemas comuns](deploy.md#problemas-comuns-compose--postgres).

Variáveis úteis:

| Var | Uso |
|-----|-----|
| `E2E_BASE_URL` | API `http://127.0.0.1:8000` ou FE `http://127.0.0.1:3000` |
| `E2E_API_TOKEN` / `API_TOKEN` | Header `X-API-Token` nos testes API |
| `E2E_LIVE=1` | Playwright contra stack real |
| `E2E_ANALYSIS_ID` | analysis_id já `completed` (review/SEI/Art.6 na UI) |
| `E2E_DOCUMENT_ID` | document_id com análise (opcional) |

## Camada 0 — Smoke Compose

```bash
chmod +x scripts/smoke_e2e_compose.sh
./scripts/smoke_e2e_compose.sh
```

Valida `/livez`, `/readyz`, frontend e BFF `/api/proxy/{documents,moldes,comparison,fornecedores}`.

## Camada 1 — API HTTP

```bash
# Rápidos (sem LLM longo)
E2E_BASE_URL=http://127.0.0.1:8000 PYTHONPATH=backend:e2e/tests \
  pytest e2e/tests -m e2e_fast -v --tb=short

# Suite histórica (LLM real + worker) — ~17 testes + live
E2E_BASE_URL=http://127.0.0.1:8000 PYTHONPATH=backend:e2e/tests \
  pytest e2e/tests -m "e2e_live or e2e_full_flow" -v --tb=short

# Tudo
E2E_BASE_URL=http://127.0.0.1:8000 PYTHONPATH=backend:e2e/tests \
  pytest e2e/tests -v --tb=short
```

Fixture DOCX: `python e2e/scripts/generate_fixture.py` se faltar `e2e/fixtures/sample-tr.docx`.

## Camada 2 — Playwright UI

```bash
cd frontend
E2E_LIVE=1 E2E_BASE_URL=http://127.0.0.1:3000 \
  E2E_ANALYSIS_ID=<uuid-opcional> \
  npx playwright test
```

P0 cobre: rotas, BFF lists, upload TR (longo), proposta sem análise TR, review/SEI/Art.6 (precisa `E2E_DOCUMENT_ID` ou skip).

## Critério de aceite

- [ ] Camada 0 verde
- [ ] `e2e_fast` verde
- [ ] Playwright P0 (exceto cenários skip explícitos) verde
- [ ] Suite live 17/17 quando houver cota LLM + worker

## Regressões críticas

1. Upload **proposta** não chama `POST .../analysis/.../start`
2. BFF não monta `/api/v1/v1/...`
