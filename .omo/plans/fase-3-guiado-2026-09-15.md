# Fase 3 — UX guiada "Revisar agora" (mini-plano)

> Branch: `feat/revisor-inteligente-15-09` (pós-higiene `3351a6d`).
> Princípio: **menos denso, mesmo dado, mesmo `CorrectionCard`**. Um passo por vez + progresso
> explícito + saída clara para o SEI. Zero duplicação de lógica.

## Objetivo

Habilitar modo **Guiado** sobre a page de análise atual: o elaborador vê 1 correção prioritária
por vez (crítico/alto + estrutural = `isPriorityCorrection`), decide (aprovar/rejeitar/ajustar),
avança. Resto da UI (lista completa, relatório, Art.6) fica atrás de "Ver todas". Substitui a
densidade do grid por foco sequencial, sem reescrever `CorrectionCard`.

## Decisões (julgamento sênior)

- **Não criar rota nova**: guided é toggle na mesma page (`priority` já existe como estado).
  Menos rota = menos manutenção + sem quebrar links/E2E.
- **Reúso estrito**: `CorrectionCard` + `filterPriorityCorrections` + `useAnalysisPage` continuam.
  Novo código só orquestra ordem e progresso.
- **Pendências reais, não snapshot**: lista = `filterPriorityCorrections(corrections,'priority')`
  filtrado por `review_status===pendente`, ordenado por severidade (crítico→alto) + estrutural.
  Ao aprovar/rejeitar, a própria `onReviewUpdated` remove da fila e o índice avança sozinho.
- **Estado local, sem backend novo**: `currentIndex` + `guidedActive`. Persistência é a revisão já
  existente (`PATCH /corrections/{id}`) — guiado só navega.

## Arquivos

- Novo: `frontend/src/components/analysis/GuidedReview.tsx` (≤200 linhas: progresso + correção atual + navegação).
- Alterar: `frontend/src/app/analysis/[id]/page.tsx` (trocar CTA "Revisar agora"/"Ver todas" por
  toggle Guiado; quando guiado, renderizar `GuidedReview` no lugar do grid).
- Nada em backend. `ItemList`/`ItemDetail` permanecem para modo "Ver todas".

## Fluxo

```
[Header]  Copiar pacote SEI (só quando há aprovada/ajustada) — inalterado
[Banners + Art6] — inalterados
[CTA]  Revisar agora (Guiado)  |  Ver todas
  └─ Guiado:  3 de 9 · Barra  · `<CorrectionCard>` da vez · Anterior/Próxima · Sair do guiado
  └─ Ver todas: grid atual (lista + detalhe) — como está hoje
```

Entrada guiado vazia: mensagem "Nenhuma pendência prioritária — veja todas ou vá ao relatório".

## Limites

- Arquivos novos/alterados em ≤300 linhas cada (guiado ≈180, page após ≈200).
- Nenhum novo `data-testid` obrigatório (E2E existentes preservados); opcional `data-testid="guided-*"` para futuro.
- DPIA/segurança: nenhuma mudança (mesma revisão humana, mesma validação de placeholders).

## Verificação

- `tsc --noEmit` 0 + `npm run build` OK
- `pytest 265` inalterado
- Smoke 4 healthy
- Manual: guiado com 0, 1 e 9 pendências; aprovar no guiado remove da fila e atualiza nota/risco;
  "Ver todas" continua idêntica; "Copiar pacote SEI" só após aprovada/ajustada.
