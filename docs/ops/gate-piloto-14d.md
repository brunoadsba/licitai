# Gate piloto 14 dias + DOCX condicional

**Status:** pendente de execução (código das Fases A–F já entregue). Janela de uso real após merge/deploy.

Não é feature de código até o gate falhar no desfecho HTML.

## Métricas-alvo (14 dias)

| Métrica | Alvo | Status |
|---------|------|--------|
| Sessões com pacote SEI ou HTML | ≥ 50% | A medir |
| Rejeição humana em alto/crítico | tendência de queda vs semana 1 | A medir |
| `completed_with_errors` / semana | estável ou ↓ (modo econômico) | A medir |
| HTML skips / aprovadas | &lt; 10% | A medir |

Anotar no fim de cada semana no Painel (card saúde + pendências) e em planilha local.

## Como iniciar o gate

1. Deploy / subir stack com worker + `.env` com `+asyncpg`.
2. Agendar `backup_daily.sh` e `ops_alerts.sh`.
3. Usar fluxo: Enviar TR (modo econômico) → Prioridade + Art. 6 → aprovar → pacote SEI / HTML.
4. Ao fim de 14 dias, preencher a tabela acima e decidir DOCX.

## DOCX

**Status (código):** disponível — `GET /api/v1/analysis/{id}/corrected-docx` e botão **Baixar DOCX** na análise.

Continua recomendável validar no SEI real se o HTML/pacote basta; o DOCX cobre o caso em que o Word nativo é necessário.
