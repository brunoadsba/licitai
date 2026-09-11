# Ops piloto LicitAI (sem CI / sem Kubernetes)

Checklist operacional do elaborador de TR em ambiente single-user.

## Status (código vs pendências humanas)

| Item | Status |
|------|--------|
| Fases A–F (medir, HTML, Art. 6, economic, qualidade docs/smoke, alertas) | **Feito** em `main` |
| Export DOCX do TR corrigido | **Feito** (`GET /analysis/{id}/corrected-docx` + botão na análise) |
| Art. 6 cobertura estrutural (`art6_coverage` ≥90%) | **Feito** (API/UI + `score_art6_fixtures.py`); baseline fixtures ~71% |
| UI tema claro/escuro | **Feito** (toggle no header; ver [frontend/DESIGN.md](../../frontend/DESIGN.md)) |
| UX fluxo elaborador + guia | **Feito** em `feat/ux-fluxo-elaborador` ([docs/guia-usuario.md](../guia-usuario.md), app `/guia`); BFF `/api/proxy` corrigido (11/09) |
| Fixtures TR CODEBA (12 objetos) | **Feito** em `fixtures/trs-codeba/` (PDFs gitignored) |
| Cron backup diário + alertas | **Feito neste host** via `./scripts/install_ops_cron.sh --apply` — ver [cron.md](cron.md) |
| Backup dry-run | **Feito** (`scripts/backup_daily.sh` → `backups/licitai_*`) |
| Gate 14 dias de uso real CODEBA | **Pendente** (Bruno / elaboradores) — [gate-piloto-14d.md](gate-piloto-14d.md) |
| Rotação de secrets | **Pendente** (manual) |
| Benchmark quinzenal com 5 TRs CODEBA | **Pendente** (rotina) — [piloto-qualidade.md](piloto-qualidade.md) · fixtures em `fixtures/trs-codeba/` |
| CI GitHub / K8s / fine-tune / multi-tenant | **Fora de escopo** (não fazer) |

## Secrets (manual Bruno)

1. Rotacionar `GROQ_API_KEY` / `GEMINI_API_KEY` / `POSTGRES_PASSWORD` / `API_TOKEN` quando conveniente.
2. Em `.env`, use driver async: `DATABASE_URL=postgresql+asyncpg://...` (nunca só `postgresql://` para a API).
3. `.env` em **LF** (não CRLF). Preferir `./scripts/up.sh` (já faz `unset POSTGRES_PASSWORD DATABASE_URL`). Se subir na mão sem o script, o shell pode sobrescrever o `.env` e deixar o backend `unhealthy`. Detalhes: [deploy.md](deploy.md#problemas-comuns-compose--postgres).

## Subir / parar stack (Compose)

```bash
./scripts/up.sh            # dia a dia (após ligar o PC / Docker)
./scripts/up.sh --build    # após mudança de frontend/imagem
./scripts/down.sh          # opcional antes de desligar; não apaga dados
```

UI: `http://127.0.0.1:3000/` · API: `http://127.0.0.1:8000/`.

## Backup e alertas (cron)

Ver [cron.md](cron.md). Comandos rápidos:

```bash
./scripts/install_ops_cron.sh --apply
./scripts/backup_daily.sh
./scripts/ops_alerts.sh http://127.0.0.1:8000
```

Restore: [restore-drill.md](restore-drill.md). Drill trimestral recomendado.

## Modelos LLM (pin)

Evite aliases `*-latest` em produção sem smoke. Defaults atuais no Compose:
- Groq: `openai/gpt-oss-20b`
- Gemini: pin explícito no `.env`

```bash
./scripts/smoke_llm.sh
# LLM_SMOKE_REAL=1 ./scripts/smoke_llm.sh
```

Modo padrão do piloto: **economic** (jurídico + Art. 6). Orçamento opcional: `ANALYSIS_MAX_LLM_CALLS` (0 = ilimitado).

## Qualidade e gate 14 dias

- [piloto-qualidade.md](piloto-qualidade.md) — rotina quinzenal (**execução pendente**)
- [gate-piloto-14d.md](gate-piloto-14d.md) — critérios de uso real (**janela não iniciada**)
- Meta estrutural Art. 6º: **≥90%** (`art6_coverage` na API/UI). Score local sem LLM:

```bash
PYTHONPATH=backend python backend/scripts/score_art6_fixtures.py
```

## Frontend (piloto)

- URL: `http://127.0.0.1:3000/` (Compose) — ver seção Subir / parar stack
- Tema claro/escuro: botão Sol/Lua no header (`licitai-theme` no `localStorage`)
- Design: [frontend/DESIGN.md](../../frontend/DESIGN.md)

## Checklist 14 dias (valor) — pendente de medição

1. Tempo até 1ª revisão crítica
2. % sessões com pacote SEI / HTML / DOCX
3. Taxa rejeição humana alto/crítico
4. Taxa `completed_with_errors` / semana
5. Cobertura Art. 6 média (`art6_coverage`) nas sessões do gate

SLOs: [slos.md](slos.md).
