# Reconhecimento de arquitetura + plano de higiene e UX (15/09/2026)

> Branch: `feat/revisor-inteligente-15-09` (base `main` `2669627`).
> Regras desta frente: **planejar antes de executar** (cada fase vira plano próprio + revisão antes de implementar);
> **reaproveitar o que existe** (nada de reescrever); **arquivos de app em 200–300 linhas**;
> **UX simples, menos densa**. Sem merge antes de 28/09 se algo tocar na régua do gate.

## 1. Retrato atual (medido, não achado)

- **Escala**: ~202 arquivos fonte em `backend/app` + `frontend/src` (~25,2k linhas); +73 em tests/scripts/e2e (~33,6k total).
- **Distribuição**: 14 arquivos >300 linhas · 22 entre 201–300 · 167 com ≤200. Ou seja: **a base já é majoritariamente pequena** — o problema está concentrado em ~14 arquivos.
- **Arquitetura backend (disciplinada, em camadas)**: `api/` (routers) → `services/` por domínio
  (agents 8, analyzer 12, chat 7, comparator 7, email 1, embeddings 4, generator 2, jobs 2,
  legal 2, llm 6, parser 8, rag 5, rules 4) → `models/` + `schemas/` → `worker.py` (fila durável).
  Fluxo: upload → parse (job) → `start_analysis` (enqueue) → worker → `engine.run_analysis` →
  orquestrador multi-agente → corrections → revisão humana → `recalculate_analysis_scores` → SEI/HTML/DOCX.
- **Frontend (bom padrão já estabelecido)**: routes por domínio + `components/<dominio>/` +
  hooks (`useUploadAnalysisPipeline`, `useChat`, `useCopy`) + `lib/` utilitário + BFF `/api/proxy`.
  Componentes de análise (`CorrectionCard`, `ItemDetail`, `CorrectionReviewActions`, `priorityQueue`)
  já são pequenos e coesos — **são o modelo a seguir**, não o problema.

## 2. Os 14 arquivos >300 (alvo cirúrgico, resto não toca)

| Arquivo | Linhas | Diagnóstico | Split proposto (mover, sem mudar comportamento) |
|---|---|---|---|
| `backend/app/api/analysis.py` | 953 | Mistura endpoints + scoring + snapshot + exports SEI/HTML/DOCX + report + pending_summary | `analysis.py` (start/review) + `analysis_scoring.py` + `analysis_snapshot.py` + `sei_exports.py` + `report.py` (~5× 150–250) |
| `frontend/src/app/analysis/[id]/page.tsx` | 620 | Página-orquestra: header, 2 dropdowns, banners, polling, exports, lista+detalhe | Extrair `useAnalysisPage.ts` (estado+polling) + `AnalysisHeader.tsx` + `AnalysisBanners.tsx`; page vira composição ~150 |
| `frontend/src/lib/api.ts` | 614 | Cliente único p/ todos os domínios | `api/client.ts` + `api/documents.ts` + `api/analysis.ts` + `api/comparison.ts` (+ re-export no `api.ts` p/ não quebrar imports) |
| `backend/app/services/analyzer/engine.py` | 543 | `run_analysis` gigante (~300 linhas) | Extrair `analysis_runner.py` (concorrência) + `cross_review.py`; engine fica orquestração ~200 |
| `backend/app/services/parser/detection.py` | 384 | Coeso (heurísticas), só grande | `toc.py` + `headings.py` + `substantive.py` (~3× ~130) |
| `backend/app/api/comparison.py` | 368 | Endpoints + matriz + feedback | `comparison.py` + `matrix.py` + `feedback.py` |
| `frontend/src/app/report/[id]/page.tsx` | 361 | Mesmo padrão da analysis | Mesma receita: hook + componentes, page ~150 |
| `backend/app/api/documents.py` | 351 | CRUD + diff de versões + token estimates | `documents.py` + `document_diff.py` |
| `backend/app/worker.py` | 323 | Loop + handlers de job + orphans + heartbeat | Handlers → `services/jobs/handlers.py`; worker fica loop+saúde ~200 |
| `comparacao/versoes/page.tsx` | 313 | Limítrofe | Só se tocar no arquivo por outro motivo |
| `services/rules/extractor.py` | 312 | Limítrofe | Idem |
| `services/llm/provider.py` | 304 | Limítrofe | Idem |
| `frontend/src/types/index.ts` | 411 | Types de todos os domínios num arquivo | `types/documents.ts` + `types/analysis.ts` + `types/comparison.ts` (+ re-export; move puro, risco mínimo) |
| tests grandes (`test_chat_api` 480, `test_sei_pack*` 347, `test_engine` 330, `benchmark.py` 330) | — | Teste golden/E2E tende a ser longo | **Proposta: isentar tests/scripts da regra** (vale p/ código de app); dividir só se virar dor de manutenção |

## 3. Suspeitas de peso morto (confirmar na Fase 0, não remover no escuro)

- `frontend/src/app/wizard/` e `frontend/src/app/design/`: **fora do Sidebar**; só citadas no `Header.tsx`
  como mapa rota→título (`/wizard: 'Enviar TR'`). Cheiro de rota órfã (wizard provavelmente virou `/upload`).
  Ação: confirmar sem links/redirects → remover ou redirecionar, nunca manter zumbi.
- `gerar-tr/`, `moldes/`, `comparacao/`: linkadas no Sidebar — vivas, não tocar.
- `__pycache__/`: ruído de contagem, irrelevante.

## 4. UX: por que está densa e a cura (progressive disclosure)

- **Densa onde dói**: a página de análise empilha header + 2 dropdowns (Exportar/Mais) + banners
  (progresso, erro, `completed_with_errors`) + toggle prioridade/tudo + lista de itens + detalhe com
  cards DE→PARA + fundamentação + 2 níveis de "copiar SEI". O elaborador vê tudo de uma vez.
- **Cura sem reescrever**: modo **"Revisar agora" guiado** — 1 correção por vez (sugestão → aprovar /
  rejeitar / ajustar → próxima), progresso `X/9`, resto (lista completa, relatório, exports) escondido
  até o fim. Reaproveita `CorrectionCard`, `filterPriorityCorrections`, `countPendingPriority` como estão.
- **Bônus arquitetural**: esse fluxo guiado é exatamente a cama onde o **revisor-assistente** deita
  depois (sugestão pré-preenchida + confiança, 1 clique para confirmar). UX simples primeiro,
  inteligência em cima — nessa ordem.

## 5. Ordem de execução (fases, cada uma com plano próprio + revisão)

- **Fase 0 — Inventário fino (sem código)**: confirmar órfãs (wizard/design), mapear imports dos 14 alvos,
  travar baseline (265 passed + smoke). Entrega: checklist de splits com risco por arquivo.
- **Fase 1 — Splits backend** (analysis.py → documents/comparison → engine/detection → worker),
  um arquivo por vez, teste verde entre cada. Nenhum comportamento muda; régua do gate intacta.
- **Fase 2 — Splits frontend** (types → api.ts → pages), com re-export p/ zero quebra de imports.
- **Fase 3 — UX "Revisar agora" guiado** (única fase com mudança visível; validar com uso real).
- **Fase 4 — Revisor-assistente** sobre a base limpa (checagens determinísticas + 2ª opinião + confiança).

## 6. Verificação por fase

- Split: `pytest backend/tests -q` 265 passed + `tsc` exit 0 + smoke antes/depois; diff só move código.
- UX: uso real do fluxo guiado (tempo até pacote SEI) + sem regressão no fluxo atual (mantido em paralelo).
- Nunca: auto-aprovação, mudança de scoring, merge de régua antes de 28/09.

## 7. Resultado execução Fase 0–2 (15/09, branch `feat/revisor-inteligente-15-09`, sem commit)

- **Fase 0**: `/wizard` = redirect proposital p/ `/upload` (manter); `/design` = showcase dev-only (manter).
  Nada removido. Baseline travada: 265 passed + smoke 4/4.
- **Fase 1 (backend, 265 passed + smoke OK no fim)**:
  `api/analysis.py` 953 → 8 módulos (maior 230; + correção de ordem: review antes de details p/ `/pending-summary`
  não ser engolido por `/{analysis_id}`, + imports atualizados em `documents.py` e 5 testes);
  `documents.py` 351→290 (+`document_diff.py` 76); `comparison.py` 368→247 (+`comparison_matrix.py` 139);
  `engine.py` 543→207 (+`item_selection` 69, `analysis_phases` 125, `analysis_persistence` 247);
  `detection.py` 384→4 módulos (66/123/127/88, sem fachada); `worker.py` 323→290 (+`jobs/handlers.py` 49).
- **Fase 2 (frontend, tsc 0 + `npm run build` OK)**:
  `types` 411→barrel+4 domínios; `lib/api` 614→barrel+6 (`client/documents/analysis/comparison/generator/chat`);
  page análise 620→192+hook 293+header 198+banners 81; page relatório 361→115+6 seções.
  `data-testid`s preservados (E2E intactos).
- Restam >300 só os 3 limítrofes isentos: `versoes/page` 313, `extractor` 312, `provider` 304.
- **Fase 3 (15/09, committed higiene `3351a6d`) — UX guiada "1 por vez"**: mini-plano `fase-3-guiado-2026-09-15.md`;
  `GuidedReview.tsx` 138 linhas (progresso + 1 `CorrectionCard` + navegação) integrado na page análise
  218 linhas (toggle Guiado ↔ Ver todas, reúso total do card/priorityQueue, data-testid preservados);
  `tsc 0` + build frontend OK + `pytest 265` + smoke 4 healthy.
- **Fase 4 — revisor-assistente**: scoping `fase-4-revisor-assistente-2026-09-15.md` (consultivo, fail-closed,
  1 clique para aceitar sugestão, sobre o guiado; sem código nesta etapa, sem auto-aprovação antes de 28/09).
