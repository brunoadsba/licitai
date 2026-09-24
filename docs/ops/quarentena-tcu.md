# Quarentena TCU (Fase 0B)

Fontes TCU ingeridas por `backend/scripts/ingest_juris_tcu.py` não têm URL oficial específica (apenas a busca genérica `pesquisa.apps.tcu.gov.br`) e misturam enunciado com comentário. Elas **permanecem no banco** e saem da recuperação padrão até confirmação jurídica.

Lista máquina: [backend/data/tcu/pending-confirmation.json](../../backend/data/tcu/pending-confirmation.json).

## Itens em quarentena

| law_number | Motivo |
|------------|--------|
| Súmula 247/TCU | URL genérica; enunciado + comentário Lei 14.133 |
| Súmula 272/TCU | URL genérica; enunciado + comentário Lei 14.133 |
| Acórdão 1214/2013-TCU-Plenário | URL genérica; atribuição sem fonte específica |

## O que o código faz

- `retrieve()` e os backends de busca excluem esses `law_number` e qualquer documento com `version` prefixo `quarantine`.
- `legal_basis` que cita esses itens é anulado na persistência e no parecer/SEI.
- Consulta cuja única fonte seria material em quarentena recebe mensagem de ausência de fonte (chat).
- O script de ingestão grava `version=quarantine-0B` e **não** reativa a busca.

## Marcar o banco piloto (não apaga)

```bash
# dry-run (padrão)
docker compose exec -T backend python scripts/quarantine_tcu.py

# apply
docker compose exec -T backend python scripts/quarantine_tcu.py --apply
```

## Reingestão

Só após URL oficial específica, título oficial, data de coleta, hash, separação enunciado/comentário e revisão jurídica. Não usar `https://pesquisa.apps.tcu.gov.br/` como fonte específica.
