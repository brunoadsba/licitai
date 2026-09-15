# Fase 4 — Revisor-assistente inteligente (scoping, sem código)

> Objetivo: tornar o gate o mais autônomo possível, mas **fail-closed**: IA sugere, humano decide.
> Sobre a base limpa da higiene + Fase 3 (guiado). Nada vai para cloud; dado CODEBA fica local.

## O que já existe e será reaproveitado

- `PATCH /corrections/{id}` + `recalculate_analysis_scores` (exclui rejeitadas → nota/risco recalculam)
- `CorrectionCard` + `CorrectionReviewActions` (aprovar/rejeitar/ajustar com placeholders bloqueados)
- `GuidedReview` (Fase 3) — 1 por vez, grave primeiro; é a cama perfeita p/ plugar sugestões
- `promote_feedback.py` (thumbs-down → `e2e/golden/feedback/` → dataset de precision)
- `analysis_persistence` (grounding + fail-closed jurídico já validam `original_text` e `legal_basis`)
- Métricas `review_*` + `art6_coverage`

## O revisor-assistente (consultivo, não autônomo)

Fase 4 é um **segundo parecer**, não um auto-aprovedor:

```
Determinístico (local, 0 LLM)                | LLM 2ª opinião (local/Ollama, fail-closed)
- original_text está no item? (grounding)    | - o problema apontado procede?
- placeholders pendentes?                     | - a correção resolve sem criar risco?
- severity vs category coerente?              | - o fundamento cita lei certa?
- score/risco se rejeitar/aprovar?            | - confiança 0–1 + justificativa curta
```

Saída por correção: `sugestão {aprovar|rejeitar|ajustar} + confiança + motivo + evidências`
Sem `confiança ≥ 0.95` em severidade baixa → nunca sugerir auto-ação; sem humano, nada vai para o SEI.

## UX (em cima do guiado)

No `GuidedReview`, acima do `CorrectionCard` atual, um banner sutil:

> **Sugestão do revisor (confiança 82%) — aprovar.** Motivo: grounding OK + legal_basis válido no RAG.
> [Aceitar sugestão] [Ver detalhes]

- Um clique = preenche `review_status` e chama o mesmo `onReviewUpdated` (sem código duplicado).
- Crítico/alto nunca com botão "aceitar" sem abrir o card (abre o `CorrectionReviewActions`).
- Baixa confiança → banner amarelo: "revisar com atenção — evidência fraca".

## Backend (escopo mínimo, sem quebrar a regra 200–300)

- Novo `backend/app/services/reviewer/` (≤200 linhas total):
  - `checks.py` — checagens determinísticas puras (sem IO) + cálculo de confiança
  - `second_opinion.py` — chamada opcional ao LLM local (Ollama) com prompt curto; se OFF ou 429, devolve só checagens
  - `schemas.py` — `ReviewSuggestion` (pydantic)
- Novo `backend/app/api/reviewer.py` (≤150 linhas):
  - `GET /analysis/{id}/review-suggestions` → lista de sugestões para as pendentes
  - `GET /analysis/{id}/review-suggestions/{correction_id}` → uma
  - Reúso de `_filter_corrections` + `is_substantive_content`; sem mexer em scoring
- Frontend: `frontend/src/lib/api/reviewer.ts` + `frontend/src/components/analysis/ReviewSuggestionBanner.tsx`
  Integrado no `GuidedReview` e, opcionalmente, como selo no `CorrectionCard`.

## Dados e evolução

- Cada decisão humana (aprovar/rejeitar/ajustar + nota) já é logada; Fase 4 só expõe `suggestion vs decisão`
  para medir precision do assistente contra você — sem treinar nada antes de 28/09.
- `promote_feedback` continua como golden; quando o assistente errar feio, o erro vira caso de teste.

## Fora de escopo agora

- Auto-aprovação (Só após gate + dataset estável + precision ≥ 0.95 em baixa severidade)
- Novas migrações Alembic
- Mudança de scoring/regra do Art. 6 (muda a régua do gate)
- Fine-tune/custom model antes do gate fechar

## Verificação planejada

- `GET /review-suggestions` com fixtures: correção com grounding ok → aprovar alta confiança;
  com placeholder → ajustar; com `legal_basis` inválido → rejeitar/low.
- UI: banner aparece no guiado, "Aceitar" chama o mesmo fluxo humano, sem bypass de placeholders.
- `pytest` + `tsc` + smoke inalterados; `types`/`api` barrels mantêm imports.
