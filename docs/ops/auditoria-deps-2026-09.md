# Dependências: residual aceito + rotina mensal (28/09/2026)

Baseline: `docs/ops/audits/2026-09-28.md` (gerado por `scripts/audit_deps.sh`).

## Frontend — residual aceito (não migrar agora)
- `next@14.2.35` (última 14.x): audit ainda acusa crítica genérica (faixa cobre até 16.x).
  Zerar exige Next 15/16 (React 19, breaking) — fora de escopo do piloto.
- Por que não nos atinge hoje: sem `middleware`, sem `next/image`, sem servidor
  custom, containers Linux, acesso só via `127.0.0.1`, 1 usuário. CVEs acusados
  exigem essas superfícies (RCE Windows, AVIF, i18n Pages Router, custom server).
- `postcss`/`nanoid` aninhados: só saem com `--force` (pularia p/ Next 16). Não fazer.
- Gatilhos p/ migrar: piloto sair do localhost/multiusuário, ou CVE em caminho
  usado de verdade (rewrites, RSC, BFF). Reavaliar nesses casos.

## Backend — reavaliar com calma (fora da Fase 1)
- 30 vulns em 3 transitivos (`starlette`, `python-multipart`, `pdfminer-six`).
- Candidatos menores existem (`starlette 0.47.2`, `multipart 0.0.22`), mas bump de
  transitivo mexe com FastAPI — fazer em branch própria com suíte verde, não agora.

## Rotina mensal
1. `./scripts/audit_deps.sh` (só reporta, nunca altera).
2. Comparar com o mês anterior em `docs/ops/audits/`.
3. Só agir se: CVE novo em superfície usada, ou fix patch-level sem breaking.
