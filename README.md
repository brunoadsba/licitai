# LicitAI

Sistema especialista para análise de Termos de Referência (TR) de licitações públicas, com foco nas Leis 14.133/2021 e 13.303/2016, RILC CODEBA, AGU e CGU.

Piloto CODEBA, single-user. O elaborador envia o TR, revisa só o que importa (alto/crítico + Art. 6º) e leva ao SEI apenas o que **aprovou** ou **ajustou**.

**Guia do elaborador:** [docs/guia-usuario.md](docs/guia-usuario.md) (também em `/guia` na UI)  
**Ops do piloto:** [docs/ops/piloto.md](docs/ops/piloto.md)  
**Memória do projeto:** [memory.md](memory.md)

## Estado (24/09/2026)

Código das fases **0A–8** está em `main`. Schema esperado: `20260924_004`.

| Feito | Pendente (humano) | Fora de escopo |
|-------|-------------------|----------------|
| Sigilo fail-closed, quarentena TCU, token operacional | Visto jurídico (eval + amostra 14.133/13.303) | CI GitHub, K8s, fine-tune |
| Ingestão idempotente, modelo jurídico versionado | URLs oficiais TCU (sair da quarentena) | Multi-tenant / OIDC |
| FTS Postgres, grounding, custo, auditoria | Gate 14 dias, colar SEI real, rotação de secrets | LangGraph |
| Pacote SEI / HTML / DOCX | Ollama se for usar TR `sigiloso` | |

Recall@5 no corpus piloto (599 chunks): **0.357** (FTS). Semente local: 1.0. `pgvector` instalado; vetores ainda só em JSON.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | Next.js 14 (App Router), React 18, Tailwind CSS 3, TypeScript |
| BFF | Route Handler `/api/proxy/*` injeta `API_TOKEN` (o browser nunca vê o token) |
| Backend | FastAPI, Python 3.12, SQLAlchemy async, Alembic, worker asyncio |
| Banco | PostgreSQL 16 (piloto/Compose). SQLite só em `APP_ENV=development` |
| IA | Groq, Gemini (cloud) ou Ollama (local). Failover simétrico. Cloud bloqueada para `sigiloso`/`NULL` |

## Como subir

### Compose (recomendado no WSL)

```bash
./scripts/up.sh            # unset env sujo + compose up -d + smoke
./scripts/up.sh --build    # após mudança de frontend/imagem
./scripts/down.sh          # para containers; não apaga pgdata
```

UI: `http://127.0.0.1:3000/` · API: `http://127.0.0.1:8000/`

Copie `.env.example` para `.env`. Com Postgres, `API_TOKEN` é obrigatório. Análises só avançam com o serviço `worker`.

Frontend Docker **sem bind mount**: mudança de UI exige `--build`.

### Nativo (WSL)

```bash
# API
cd backend
PYTHONPATH=. .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Worker (outro terminal)
cd backend
PYTHONPATH=. .venv/bin/python -m app.worker

# UI
cd frontend
npm run dev
```

Upload, chat e gerar-tr **exigem classificação**. Não envie `sigiloso` sem Ollama — a API responde 422 de propósito.

Runbook: [docs/ops/deploy.md](docs/ops/deploy.md). Auth do piloto: [docs/ops/auth-piloto.md](docs/ops/auth-piloto.md).

## Fluxo do elaborador

1. Enviar TR (PDF, DOCX ou ODT) com classificação.
2. Aguardar a análise (fila Prioridade).
3. Revisar em **Revisar agora** (1 por vez) ou **Ver todas**. Conferir a evidência DE→PARA.
4. Copiar pacote SEI / HTML / DOCX. O JSON de auditoria fica no menu Exportar (rastro, não vai ao SEI).

Comparações, moldes e gerar TR ficam em **Mais ferramentas**.

## Segurança (piloto)

- Token compartilhado (`API_TOKEN`) ≠ login de usuário.
- `NULL` de classificação = sigiloso. Cloud (Groq/Gemini) bloqueada.
- Upload: allowlist de extensão + magic bytes + UUID no disco.
- CSP, rate limit, CORS allowlist, imagem backend não-root.
- Swagger (`/api/docs`) só com `APP_ENV=development`.
- TCU sem URL oficial (Súmulas 247/272, Acórdão 1214/2013) está em quarentena e **não** entra na busca padrão.

## Testes

```bash
# Unitário (SQLite em memória via conftest)
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q

# Schema Postgres (parser pglast)
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_init_sql.py -q

# Eval de recuperação (semente)
cd backend && PYTHONPATH=. python scripts/eval_corpus_real.py --seed --check-baseline --baseline eval/baseline.ci.json
```

E2E Compose: [docs/ops/e2e-full.md](docs/ops/e2e-full.md). CI GitHub permanece desligado (`ci.yml.disabled`).

## Corpus jurídico

Reingestão (sequencial; não paralelizar no mesmo banco):

```bash
cd backend
PYTHONPATH=. python scripts/ingest_laws.py
PYTHONPATH=. python scripts/ingest_rilc_codeba.py
PYTHONPATH=. python scripts/ingest_juris_tcu.py
PYTHONPATH=. python scripts/ingest_embeddings.py
```

RILC: `backend/data/rilc/source/` (PDF gitignored, hash pinado). Piloto típico: 6 docs / ~599 chunks. Fontes TCU sem URL oficial saem da busca após a ingestão.

Eval: [docs/ops/eval-fase2.md](docs/ops/eval-fase2.md). Recuperação FTS: [docs/ops/recuperacao-fase5.md](docs/ops/recuperacao-fase5.md).

## Extensão SEI (opcional)

1. Chrome/Edge → `chrome://extensions` → modo desenvolvedor.
2. Carregar sem compactação a pasta `extension/`.
3. A extensão fala com o BFF em `http://127.0.0.1:3000/api/proxy` e sanitiza HTML.

## Documentação viva

| Doc | Uso |
|-----|-----|
| [docs/guia-usuario.md](docs/guia-usuario.md) | Elaborador |
| [docs/ops/piloto.md](docs/ops/piloto.md) | Checklist operacional |
| [docs/ops/deploy.md](docs/ops/deploy.md) | Compose, env, smoke |
| [docs/ops/plano-tecnico-ajustado.md](docs/ops/plano-tecnico-ajustado.md) | Fases 0A–9 |
| [memory.md](memory.md) | Contexto contínuo para agentes |
| [frontend/DESIGN.md](frontend/DESIGN.md) | Tokens e tema |
| [docs/archive/](docs/archive/) | PRDs/planos históricos |

## Licença

Uso interno — CODEBA.
