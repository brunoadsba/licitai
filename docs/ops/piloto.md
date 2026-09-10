# Ops piloto LicitAI (sem CI / sem Kubernetes)

Checklist operacional do elaborador de TR em ambiente single-user.

## Status (código vs pendências humanas)

| Item | Status |
|------|--------|
| Fases A–F (medir, HTML, Art. 6, economic, qualidade docs/smoke, alertas) | **Feito** em `feat/excelencia-piloto` |
| Export DOCX do TR corrigido | **Feito** (`GET /analysis/{id}/corrected-docx` + botão na análise) |
| Cron backup diário + alertas | **Feito neste host** via `./scripts/install_ops_cron.sh --apply` — ver [cron.md](cron.md) |
| Backup dry-run | **Feito** (`scripts/backup_daily.sh` → `backups/licitai_*`) |
| Gate 14 dias de uso real CODEBA | **Pendente** (Bruno / elaboradores) — [gate-piloto-14d.md](gate-piloto-14d.md) |
| Rotação de secrets | **Pendente** (manual) |
| Benchmark quinzenal com 5 TRs CODEBA | **Pendente** (rotina) — [piloto-qualidade.md](piloto-qualidade.md) · fixtures em `fixtures/trs-codeba/` |
| CI GitHub / K8s / fine-tune / multi-tenant | **Fora de escopo** (não fazer) |

## Secrets (manual Bruno)

1. Rotacionar `GROQ_API_KEY` / `GEMINI_API_KEY` / `POSTGRES_PASSWORD` / `API_TOKEN` quando conveniente.
2. Em `.env`, use driver async: `DATABASE_URL=postgresql+asyncpg://...` (nunca só `postgresql://` para a API).

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

## Checklist 14 dias (valor) — pendente de medição

1. Tempo até 1ª revisão crítica
2. % sessões com pacote SEI / HTML / DOCX
3. Taxa rejeição humana alto/crítico
4. Taxa `completed_with_errors` / semana

SLOs: [slos.md](slos.md).
