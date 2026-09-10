# Cron / ops do piloto

Scripts:
- [`scripts/backup_daily.sh`](../../scripts/backup_daily.sh) — RPO ≤ 24h
- [`scripts/ops_alerts.sh`](../../scripts/ops_alerts.sh) — `/readyz` + delta `llm_errors`
- [`scripts/install_ops_cron.sh`](../../scripts/install_ops_cron.sh) — instala no crontab do usuário

## Instalar

```bash
chmod +x scripts/install_ops_cron.sh scripts/backup_daily.sh scripts/ops_alerts.sh
# visualizar:
./scripts/install_ops_cron.sh
# aplicar no crontab do usuário atual:
./scripts/install_ops_cron.sh --apply
```

Variáveis opcionais:
- `LICITAI_BACKUP_LOG` — log do backup (default `$ROOT/backups/backup_cron.log`)
- `LICITAI_ALERT_LOG` — dir de alertas (default `/tmp`)
- `LICITAI_LLM_ERROR_DELTA` — limiar de delta (default `3`)

## Verificar

```bash
./scripts/backup_daily.sh
./scripts/ops_alerts.sh http://127.0.0.1:8000
crontab -l | grep LICITAI
```
