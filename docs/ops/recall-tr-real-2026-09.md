# Recall em TR real — 09-ti-pabx-nuvem (28/09/2026)

Golden: `e2e/golden/real/tr_pabx.json` (status: **v2** — 3 TPs humanos 16/09 + 18 tripwires, 17 pendentes rejeitados 0A/17R contra o PDF)

## Leitura honesta

Carimbo humano feito em 28/09: os 17 pendentes foram rejeitados (título
truncado era quebra de linha; 4.3, 4.9.1 e DDR não se sustentam no
documento — ver `e2e/golden/real/anotacao_pabx_pendentes.md`). Os 3 TPs de
16/09 (3.1.1, 3.1.2, 3.1.4 keyword "abruptamente") não foram reabertos.

Recall 0,25 (3/12) abaixo fica arquivado como validação do harness sobre o
golden v1 — não é medida real sobre o v2. Re-medir exige análise no
Postgres; em 28/09 o piloto está com **zero análises** (`SELECT count(*) FROM
analyses` = 0), então nada foi re-medido.

## v1 arquivado (harness, não recall real)

### 290c7061-unitario (`290c7061-c24d-4131-bf66-9f9a7b7ecbfc`)

- Correções avaliadas: 4
- Recall v1: **0.25** (3/12)
- FPs conhecidos reincidentes: **0/7** []

### 8cdafd60-batch5 (`8cdafd60-3720-401d-b090-efc83c154af5`)

- Correções avaliadas: 6
- Recall v1: **0.25** (3/12)
- FPs conhecidos reincidentes: **2/7** ['obrigação genérica de observância', 'subdivisões hierárquicas']

## Próximo passo

1. Gerar análise do PABX no Postgres (re-run ou upload).
2. Rodar `backend/scripts/benchmark_offline.py` contra o golden v2.
3. Ligar miss-hunter e comparar antes de decidir provedor pago.
