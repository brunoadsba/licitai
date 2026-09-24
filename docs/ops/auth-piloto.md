# Autenticação operacional do piloto (Fase 0C)

O `API_TOKEN` **não** é login de usuário. É só uma trava para a API não ficar aberta se o Compose subir sem configuração.

- Com **PostgreSQL** (Docker/piloto): `API_TOKEN` é obrigatório. Sem ele o backend não sobe.
- Com **SQLite** em development (pytest/local): o token pode ficar vazio.
- O browser nunca vê o token. O BFF Next (`/api/proxy/*`) injeta `X-API-Token`.
- A extensão do SEI fala com `http://127.0.0.1:3000/api/proxy` (mesmo BFF), não com a porta 8000.
- `/api/docs` e `/openapi.json` só existem quando `APP_ENV=development`.

## Como gerar

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Coloque o valor em `.env` (`API_TOKEN=...`). Não commite o `.env`.
