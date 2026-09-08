# Restore drill — backup LicitAI

Procedimento curto para validar RPO/RTO (ver também `slos.md`).

## Pré-requisitos

1. Backup gerado por `backend/scripts/backup.sh` (contém `db.dump` + `uploads.tar.gz`).
2. Instância Postgres vazia ou de staging (nunca rode o drill em produção sem janela).
3. Variável `DATABASE_URL` apontando para o destino.

## Passos

1. Pare API e worker (`docker compose stop api worker` ou equivalente).
2. Restaure o banco:
   ```bash
   pg_restore --clean --if-exists --no-owner -d "$DATABASE_URL" backups/licitai_TIMESTAMP/db.dump
   ```
3. Restaure uploads:
   ```bash
   tar -xzf backups/licitai_TIMESTAMP/uploads.tar.gz -C backend/
   ```
4. Suba API/worker e confira:
   - `GET /readyz` → `ready`
   - Abra um documento conhecido e uma análise `completed`
   - Confira que o arquivo físico existe em `backend/uploads/`
5. Anote duração total (RTO observado) e horário do backup usado (RPO observado).

## Critério de sucesso

- Schema e dados de negócio legíveis
- Arquivos de upload recuperados
- Sem erro em `/readyz` e em uma análise de amostra
