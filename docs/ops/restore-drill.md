# Restore drill — backup LicitAI

Procedimento curto para validar RPO/RTO (ver também `slos.md`).

## Pré-requisitos

1. Backup com `db.dump` + `uploads.tar.gz` (via `backend/scripts/backup.sh` ou `pg_dump` no container `sei-db`).
2. Instância Postgres **vazia ou de staging** com extensão **pgvector** (imagem `pgvector/pgvector:pg16`). Nunca rode o drill no Postgres de produção sem janela.
3. Variável `DATABASE_URL` apontando para o destino (ou `pg_restore` via `docker exec` no container de drill).

### Gerar backup quando o host não autentica no Postgres

Se `pg_dump` no host falhar (senha/`pg_hba`), use o container:

```bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="backups/licitai_${STAMP}"
mkdir -p "$OUT"
docker exec sei-db pg_dump -U sei_user -d sei_analise --format=custom -f /tmp/db.dump
docker cp sei-db:/tmp/db.dump "$OUT/db.dump"
docker exec sei-db rm -f /tmp/db.dump
tar -czf "$OUT/uploads.tar.gz" -C backend uploads
```

## Passos (drill isolado — recomendado)

1. Suba Postgres temporário com pgvector (não use o `sei-db` vivo):
   ```bash
   docker run -d --name licitai-restore-drill \
     -e POSTGRES_USER=drill_user -e POSTGRES_PASSWORD=drill_pass -e POSTGRES_DB=drill_db \
     pgvector/pgvector:pg16
   ```
2. Aguarde `pg_isready` e rode `CREATE EXTENSION IF NOT EXISTS vector;`.
3. Restaure o dump:
   ```bash
   docker cp backups/licitai_TIMESTAMP/db.dump licitai-restore-drill:/tmp/db.dump
   docker exec licitai-restore-drill \
     pg_restore --clean --if-exists --no-owner -U drill_user -d drill_db /tmp/db.dump
   ```
4. Valide tabelas/contagens (`\dt`, `documents`, `jobs`, `legal_chunks`) e o tar de uploads (`tar -tzf ...`).
5. Remova o container de drill (`docker rm -f licitai-restore-drill`).
6. Anote RTO (duração total) e RPO (timestamp do diretório `licitai_*`).

## Passos (restaurar no ambiente Compose — só com janela)

1. Pare API e worker (`docker compose stop api worker`).
2. Restaure o banco no destino configurado em `DATABASE_URL`.
3. Restaure uploads: `tar -xzf backups/licitai_TIMESTAMP/uploads.tar.gz -C backend/`.
4. Suba API/worker e confira `GET /readyz` → `ready` + documento/análise conhecidos.

## Critério de sucesso

- Schema e dados de negócio legíveis (inclui `legal_chunks` quando o destino tem pgvector)
- Arquivos de upload recuperados
- Sem erro em `/readyz` e em uma análise de amostra (drill Compose)

## Último drill executado (staging isolado)

| Campo | Valor |
|-------|--------|
| Data | 2026-09-10 |
| Backup | `backups/licitai_20260910T104546Z` |
| Destino | container `licitai-restore-drill` (`pgvector/pgvector:pg16`) |
| `pg_restore` | exit 0 (15 tabelas; `documents=2`, `jobs=10`) |
| Uploads | 4 arquivos no tar |
| RTO observado | ~3 s (após imagem já local) |
| Nota | Drill em `postgres:16-alpine` **sem** pgvector falha em `legal_chunks` — usar sempre a imagem com vector |