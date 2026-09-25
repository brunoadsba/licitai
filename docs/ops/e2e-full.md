# E2E full — LicitAI

Runbook das três camadas. Branch de implementação: `feat/e2e-full`.

## Auditoria com LLM (falhas recentes)

Quando precisar que um agente rode E2E e julgue F1 (1.1/`[prazo]`), F2 (Copiloto) e F3 (smoke HTTP 000):

```bash
./scripts/contexto-auditoria.sh          # bloco FATOS DO GIT
./scripts/contexto-auditoria.sh --smoke  # + smoke_readyz se a stack estiver up
```

Cole a saída + [`.cursor/contexts/auditoria-e2e-falhas.md`](../../.cursor/contexts/auditoria-e2e-falhas.md) numa conversa Agent. O briefing manda verificar, não implementar feature nem reabrir TCU/RAG 5–8.

Implementação das oportunidades (ondas 0–6): [plano-30-60-90.md](plano-30-60-90.md).

## Pré-requisitos

```bash
./scripts/up.sh --build --e2e
# stack healthy: db, backend, worker, frontend (+ BFF proxy OK)
```

Equivalente manual: `unset POSTGRES_PASSWORD DATABASE_URL` → `docker compose up -d --build` → `./scripts/smoke_e2e_compose.sh`.

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

Já coberto por `./scripts/up.sh --e2e`. Isolado:

```bash
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

P0 cobre: rotas, BFF lists, seletor obrigatório de classificação, upload TR (longo), proposta sem análise TR, review/SEI/Art.6 (precisa `E2E_DOCUMENT_ID` ou skip).

A partir da Fase 0A o upload e o gerador exigem classificação (`publico` | `interno` | `sigiloso`). Specs Playwright devem selecionar o valor antes de enviar; a API sem classificação (ou com `sigiloso`, sem Ollama) responde 422. Isso está em `e2e/tests/test_e2e_privacy.py` (`e2e_fast`) e `frontend/e2e/privacy-classification.spec.ts`.

## Critério de aceite

- [ ] Camada 0 verde
- [ ] `e2e_fast` verde (inclui 422 de classificação)
- [ ] Playwright P0 (exceto cenários skip explícitos) verde
- [ ] Playwright `privacy-classification` verde com `E2E_LIVE=1`
- [ ] Suite live 17/17 quando houver cota LLM + worker

## Regressões críticas

1. Upload **proposta** não chama `POST .../analysis/.../start`
2. BFF não monta `/api/v1/v1/...`
