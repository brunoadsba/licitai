# Arquivo histórico (não usar no dia a dia)

Documentos de planejamento, brainstorm e PRDs **já concluídos ou superados** pelo código em `main`.

**Não apagar.** Servem só para consulta / auditoria de decisões.

## Fonte da verdade (vivo)

| Onde | Uso |
|------|-----|
| [README.md](../../README.md) | Como executar e visão geral |
| [memory.md](../../memory.md) | Contexto contínuo para agentes |
| [docs/guia-usuario.md](../guia-usuario.md) | Guia do elaborador |
| [docs/ops/](../ops/) | Piloto, deploy, E2E, cron, gate 14d |

## Conteúdo desta pasta

| Arquivo | Origem |
|---------|--------|
| `ideia.md`, `ideia_plano_ferramenta_tr_sei.md` | Ideação inicial |
| `aprimoramento.md`, `analise-tr-container.md` | Notas de evolução |
| `PRD.md`, `PRD_PLANO_IMPLEMENTACAO.md`, `plano-prd-implementacao-qwen.md` | PRDs / planos longos |
| `PLANO.md` | Backlog por fases (maioria `[x]`) |
| `copiloto-consultivo.md`, `explicando-licitai.md` | Specs / onboarding antigo |

Planos de sprint em `.omo/plans/` permanecem lá (tooling); não foram movidos.

## Schema SQL legado

Migrações canônicas: `backend/alembic/`.  
Arquivos em `db/migrations/*.sql` são referência histórica — **não remover** sem validar Alembic.
