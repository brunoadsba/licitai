# Fase 4 — Acabamento do revisor-assistente (plano)

> Branch: `feat/revisor-inteligente-15-09` (pós `75ac5f3`). Base limpa, 272 passed, tsc 0.
> Objetivo: fechar o revisor consultivo sem auto-aprovação — ligar 2ª opinião local opcional,
> expor métrica de acerto e cobrir o fluxo guiado com E2E. Tudo ≤300 linhas, zero nuvem.

## Escopo

1. **2ª opinião Ollama local (opt-in):** `REVIEWER_SECOND_OPINION=1` chama `get_llm_provider()` com prompt curto
   (`{"ok":bool,"delta":-0.06..0.06,"note":...}`), ajusta confiança em ±6% e anexa "· 2ª opinião: ...".
   OFF por padrão, falha silenciosa (mantém sugestão determinística). Sem novo modelo, sem corpus.
2. **Observabilidade:** `GET /metrics` já expõe `review_suggestion_*`; adicionar painel discreto no relatório
   (`ReportSuggestionStats` — lê `/metrics` via `getMetricsSnapshot` e mostra aceitas/sobrepostas/taxa).
   Sem nova rota, sem migração.
3. **E2E guiado + banner:** 2 cenários Playwright em `frontend/e2e/` — `guided-review.spec.ts` (entra no guiado,
   aceita 1 sugestão, confere `correctionId` muda de `pendente` para aprovada) + `card-suggestion.spec.ts`
   (modo "Ver todas" exibe `card-suggestion` quando há pendência). Reúso de `data-testid` existentes.

## Fora de escopo

- Auto-aprovação, mudança de scoring/Art.6, fine-tune, K8s, CI, merge em `main` antes de 28/09.
- Novo corpus/RAG, novas tabelas, secrets.

## Arquivos

- Alterar: `backend/app/services/reviewer/second_opinion.py` (trocar `llm.agenerate` inexistente por `llm.generate`,
  parse JSON robusto, log debug), `backend/app/api/reviewer.py` (continua igual, só usa o refinamento já plugado),
  `frontend/src/components/report/ReportSuggestionStats.tsx` (novo ≤80 linhas, import em `report/[id]/page.tsx`),
  `frontend/e2e/guided-review.spec.ts` + `card-suggestion.spec.ts`.
- Nada em `extractor/provider/versoes` (já ≤300).

## Verificação

- `tsc 0` + `npm run build` (frontend) + `pytest 272+` (novos mocks para `get_llm_provider` na 2ª opinião)
- Smoke 4 healthy
- E2E contra Docker (se houver LLM local, 2ª opinião deve apenas ajustar confiança, nunca quebrar o fluxo)

## Ordem

1. Plano (este arquivo) → 2. 2ª opinião → 3. painel métrica → 4. E2E → 5. commit
