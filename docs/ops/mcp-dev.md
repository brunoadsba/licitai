# MCP dev-only (não vai para prod)

Ativar só na máquina do desenvolvedor, com credenciais via env local. Nada de segredo no repo.

| MCP | Para quê | Exemplo |
|-----|----------|---------|
| Postgres read-only | Diagnosticar fila/jobs sem `psql` na mão | `DATABASE_URL=... mcp-postgres --read-only` |
| GitHub | Abrir/ler PR e issues pelo agente | `GITHUB_TOKEN=... mcp-github` |
| Playwright/browser | QA visual 375/768/1280 + axe | `mcp-playwright` no OpenCode |

Regras: nunca em prod; DSN local apenas; `TRs reais` não saem do host.
