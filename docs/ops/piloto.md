# Ops piloto LicitAI (sem CI / sem Kubernetes)

Checklist operacional do elaborador de TR em ambiente single-user.

## Status (código vs pendências humanas)

| Item | Status |
|------|--------|
| Fases A–F (medir, HTML, Art. 6, economic, qualidade docs/smoke, alertas) | **Feito** em `feat/excelencia-piloto` |
| Gate 14 dias de uso real CODEBA | **Pendente** (Bruno / elaboradores) — ver [gate-piloto-14d.md](gate-piloto-14d.md) |
| Export DOCX do TR corrigido | **Pendente condicional** — só se HTML/pacote SEI for insuficiente |
| Cron backup diário + cron alertas | **Pendente** (agendar no host) |
| Rotação de secrets | **Pendente** (manual) |
| Benchmark quinzenal com 5 TRs CODEBA | **Pendente** (rotina) — [piloto-qualidade.md](piloto-qualidade.md) |
| CI GitHub / K8s / fine-tune / multi-tenant | **Fora de escopo** (não fazer) |

## Secrets (manual Bruno)

1. Rotacionar `GROQ_API_KEY` / `GEMINI_API_KEY` / `POSTGRES_PASSWORD` / `API_TOKEN` quando conveniente.
2. Em `.env`, use driver async: `DATABASE_URL=postgresql+asyncpg://...` (nunca só `postgresql://` para a API).

## Backup diário (RPO ≤ 24h)

```bash
chmod +x scripts/backup_daily.sh
# crontab -e
# 0 2 * * * /caminho/licitai/scripts/backup_daily.sh >> /var/log/licitai-backup.log 2>&1
```

Restore: ver [restore-drill.md](restore-drill.md). Drill trimestral recomendado.

## Modelos LLM (pin)

Evite aliases `*-latest` em produção sem smoke. Defaults atuais no Compose:
- Groq: `openai/gpt-oss-20b`
- Gemini: pin explícito no `.env`

```bash
chmod +x scripts/smoke_llm.sh
./scripts/smoke_llm.sh
# LLM_SMOKE_REAL=1 ./scripts/smoke_llm.sh
```

Modo padrão do piloto: **economic** (jurídico + Art. 6). Orçamento opcional: `ANALYSIS_MAX_LLM_CALLS` (0 = ilimitado).

## Alertas mínimos

```bash
chmod +x scripts/ops_alerts.sh
# */5 * * * * /caminho/licitai/scripts/ops_alerts.sh
```

Alerta se `/readyz` ≠ ready **ou** `llm_errors` sobe ≥ `LICITAI_LLM_ERROR_DELTA` (default 3) vs estado anterior.

## Qualidade e gate 14 dias

- [piloto-qualidade.md](piloto-qualidade.md) — rotina quinzenal (**execução pendente**)
- [gate-piloto-14d.md](gate-piloto-14d.md) — critérios; DOCX só se HTML insuficiente (**janela não iniciada**)

## Checklist 14 dias (valor) — pendente de medição

1. Tempo até 1ª revisão crítica
2. % sessões com pacote SEI ou TR HTML
3. Taxa rejeição humana alto/crítico
4. Taxa `completed_with_errors` / semana

SLOs: [slos.md](slos.md).
