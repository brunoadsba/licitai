# SLOs — LicitAI (piloto single-user)

| Indicador | Alvo (piloto) | Medição |
|---|---|---|
| Latência análise (p95, FakeLLM/dev) | < 120s para TR ≤ 30 itens | `analysis_duration_avg` em `/metrics` + logs `job.ok` |
| Latência análise (p95, LLM real) | < 10 min | mesmo |
| Taxa erro jobs (failed / completed) | < 5% em 7 dias | contadores `job_errors` + tabela `jobs` |
| Disponibilidade API | 99% mensal (piloto) | `/readyz` probes |
| RPO (backup) | ≤ 24h | `scripts/backup_daily.sh` (ou `backend/scripts/backup.sh`) |
| RTO (restore drill) | ≤ 2h | `docs/ops/restore-drill.md` |

## Alertas mínimos

- `/readyz` ≠ ready por > 5 min — script `scripts/ops_alerts.sh`
- `llm_errors` delta ≥ 3 entre execuções do alerta (estado em arquivo)
- Job `running` com `lease_until` expirado e sem reclaim > 15 min
- Taxa 5xx > 2% em 15 min

Checklist piloto: [piloto.md](piloto.md) · qualidade: [piloto-qualidade.md](piloto-qualidade.md) · gate: [gate-piloto-14d.md](gate-piloto-14d.md).

## Notas

SLOs são operacionais; qualidade jurídica (precision/golden) fica em `e2e/golden/` e não substitui RPO/RTO.

Pendências humanas/ops (gate 14d, crons, secrets): [piloto.md](piloto.md).
