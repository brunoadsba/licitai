# Golden real — PABX + próximos TRs

## Eleição dos próximos 2 (28/09, scan determinístico sem LLM)

Referência: `09-ti-pabx-nuvem` (serviço TI continuado, 16 pgs, viés 14.133).

| TR | perfil medido | por que complementa |
|----|---------------|---------------------|
| `07-obra-portaria-salvador` | **32 pgs** (maior), obra, 13.303 | natureza oposta (obra × serviço): quantitativos, cronograma, medição |
| `10-monitoramento-ambiental-pga` | 13 pgs, pregão, R$ explícitos, **Art. 6 mais baixo do lote** (MANIFEST) | lacunas conhecidas → melhor régua de recall |

Preteridos: `05-concurso` (concorrência ×6, regime próprio — bom 4º); `08-coleta`
(muito parecido com PABX: serviço contínuo); `11-epi` (compra simples, pouco risco).

## Arquivos

- `tr_pabx.json` — golden v2: 3 TPs humanos (16/09) + 17 rejeitados (28/09).
- `anotacao_pabx_pendentes.md` — carimbo dos 17 (0 aprovar / 17 rejeitar), com a prova no PDF.
- Re-medir com `benchmark_offline.py` quando houver análise no Postgres.
