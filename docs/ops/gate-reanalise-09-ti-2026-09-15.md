# Gate — Reanálise `09-ti-pabx-nuvem` (15/09/2026, sem Bruno)

> Stack local Docker (backend/worker imagem pós-incrementos), modo `economic`,
> `ANALYSIS_MAX_LLM_CALLS=24`, provedor `groq` (`openai/gpt-oss-20b`).

## IDs

- Documento (re-upload): `626cabf0-3460-4be4-85e1-c6bdcd4e9365` (257 itens; parser pós-14/09, sem bloco de sumário)
- Análise: `20de1bb8-1cb8-4c98-9184-ef1b653901a8` · Job: `6cd407d9-e7fa-4184-aee2-866e0c58ba99`

## Resultado

| Métrica | Valor |
|---------|-------|
| Duração total (upload → fim) | ~13 min (parse ~1 min + análise ~12 min; igual à sessão ouro 778 s) |
| Status | `completed_with_errors` (esperado: teto de 24 chamadas estourou → `budget_truncated=true`) |
| Itens analisados | 12/257 (priorizados §§ 1/3/4/5/7) |
| Nota / risco | 9.0 / `critico` |
| `art6_coverage` | **1.0 (100%, meta ≥90% OK)** |
| Correções | 9 (1 crítico, 4 altos, 4 baixos) |
| Tokens estimados | 236.450 |

## Artefatos (todos HTTP 200)

| Artefato | Tamanho |
|----------|---------|
| `sei-pack` | 5.578 bytes |
| `corrected-html` | 72.333 bytes |
| `corrected-docx` | 51.907 bytes |

## Para o Bruno (julgamento humano)

1. Abrir a análise `20de1bb8…` e revisar as 9 correções (1 crítica + 4 altas primeiro).
2. Se faltar cobertura em trechos substantivos: "Reanalisar faltantes" (cobre `failed_item_ids` + cortados do orçamento).
3. Colar o pacote SEI em minuta de teste e anotar rejeição consciente.
