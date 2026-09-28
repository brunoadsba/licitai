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

- `tr_pabx.json` — golden draft (3 TPs + 7 FPs de vereditos humanos no banco).
- `anotacao_pabx_pendentes.md` — planilha dos 17 pendentes p/ revisão humana.
- Protocolo: aprovar/rejeitar na UI ou na planilha → virar `expected_findings`
  (TPs) e `known_fps` aqui; re-medir com `benchmark_offline.py`.
