# Gate piloto 14 dias + DOCX condicional

**Status:** **janela aberta** — início **2026-09-14** (sessão 0 = TR ouro `09-ti-pabx-nuvem`).  
Fim previsto: **2026-09-28**. Código das Fases A–F já entregue.

Não é feature de código até o gate falhar no desfecho HTML.

## Sessão 0 (abertura)

| Campo | Valor |
|-------|--------|
| Data | 2026-09-14 |
| TR | `fixtures/trs-codeba/piloto-unico/09-ti-pabx-nuvem.pdf` |
| Analysis | `6f673b1b-bcf5-41fc-8a94-3dbf2a635109` |
| Fluxo | economic → Prioridade + Art. 6 → revisão humana → pacote SEI + DOCX |
| Detalhe | [quinzena-2026-09-14.md](quinzena-2026-09-14.md) |

Ops: cron LicitAI já ativo (`backup_daily.sh` 02:00; `ops_alerts.sh` a cada 5 min) — ver [cron.md](cron.md).

## Métricas-alvo (14 dias)

| Métrica | Alvo | Status |
|---------|------|--------|
| Sessões com pacote SEI ou HTML | ≥ 50% | Sessão 0: **sim** (SEI + DOCX) |
| Rejeição humana em alto/crítico | tendência de queda vs semana 1 | Semana 1 baseline: **90%** (9/10 na sessão ouro) |
| `completed_with_errors` / semana | estável ou ↓ (modo econômico) | Semana 1: **1** (orçamento LLM) |
| HTML skips / aprovadas | &lt; 10% | A medir |

Anotar no fim de cada semana no Painel (card saúde + pendências) e em planilha local.

## Como iniciar o gate

1. Deploy / subir stack com worker + `.env` com `+asyncpg`. (**feito** — `./scripts/up.sh`)
2. Agendar `backup_daily.sh` e `ops_alerts.sh`. (**feito** neste host)
3. Usar fluxo: Enviar TR (modo econômico) → Prioridade + Art. 6 → aprovar → pacote SEI / HTML. (**sessão 0 feita**)
4. Ao fim de 14 dias, preencher a tabela acima e decidir se HTML/pacote basta vs DOCX no SEI real.

Free tier: manter `ANALYSIS_MAX_LLM_CALLS=24` e `ANALYSIS_CONCURRENCY=1` no Compose (TRs grandes → 100+ itens sem orçamento).

## DOCX

**Status (código):** disponível — `GET /api/v1/analysis/{id}/corrected-docx` e botão **Baixar DOCX** na análise.

Continua recomendável validar no SEI real se o HTML/pacote basta; o DOCX cobre o caso em que o Word nativo é necessário. Sessão 0 gerou DOCX (~53 KB) com sucesso.
