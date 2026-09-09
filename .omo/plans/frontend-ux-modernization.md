# Plano: Modernização UX/UI do Frontend LicitAI

> Data: 25/08/2026 · Branch alvo: `main` (trabalhar em branch `feat/ux-modernization`)
> Fonte da auditoria: leitura direta de `frontend/src/**` (globals.css, tailwind.config.js, layout, Sidebar/Header, dashboard, analysis, ConfirmDialog) + greps de ícones/responsividade/foco.

## 1. Contexto e Decisões Confirmadas pelo Usuário

| Decisão | Escolha |
|---|---|
| Direção estética | **Dark premium refinado** — execução nível Linear/Supabase; manter identidade dark, elevar o material |
| Mobile | **Responsivo completo** (drawer + layouts empilhados, 375/768/1280px) |
| Stack | **Completa**: `@radix-ui/*`, `lucide-react`, `sonner`, `framer-motion`, `clsx`+`tailwind-merge` |

### Princípios (do skill de redesign)
- **Evolução, não rewrite**: manter Next 14.2.21 + React 18.3.1 + Tailwind **v3.4** (não migrar para v4 neste plano). Não quebrar os 9 fluxos existentes.
- Nenhum passo avança sem o anterior validado (`tsc --noEmit` limpo após cada fase).
- Zero emojis como ícones; motion só onde comunica estado/affordance.

## 2. Achados da Auditoria (resumo executável)

**P0**: (1) sem mobile — sidebar fixa 256px + `ml-64`, 5 usos de breakpoint no app todo; (2) status fake "IA Ativa"/"Sistema operacional" hardcoded; (3) sem toasts; (4) Inter via `@import` CSS (sem `next/font`).
**P1**: (5) SVGs Heroicons inline duplicados + ~30 emojis em 10 arquivos; (6) estética AI-gradient genérica (indigo #6366f1 + glow + text-gradient); (7) botões sem `focus-visible`; (8) breadcrumb quebra em `/gerar-tr` e `/comparacao/versoes`; (9) sem error boundary por rota; (10) `min-h-screen` vs `100dvh`.
**P2**: (11) sem DESIGN.md/tokens semânticos; (12) primitivos à mão sem Radix (ConfirmDialog ok mas sem focus trap); (13) nenhuma lib de UI.

**Manter (pontos fortes)**: `.glass-card`/`.btn-*` centralizados, skeletons/empty states existentes, `aria-live`, `prefers-reduced-motion`, páginas <280 LOC, zero `any`.

## 3. Contrato de Design (conteúdo mínimo do DESIGN.md — Fase 0 produz o arquivo)

- **Material**: vidro real = tint de fundo + `backdrop-blur` + borda interna 1px (rim light) + sheen sutil; sombras tingidas com a cor do fundo (nunca preto puro). Noise/grain overlay opcional a 2–3%.
- **Cor**: base carvão profundo azulado (não `#020617` puro); rampa OKLCH multi-stop (≥5 stops); **um único accent dessaturado (<70% sat)** substituindo o indigo-AI-gradient — proposta: ciano-petróleo; semânticos de risco mantidos (verde/amarelo/laranja/vermelho) recalibrados para mesma saturação.
- **Tipo**: display + body (Geist Sans ou Satoshi via `next/font`) + mono com `tabular-nums` para notas/números/tamanhos. Escala com pesos 400–700, tracking negativo em display.
- **Motion tokens**: durações 150/250/400ms; springs do framer-motion para entradas (stagger ≤50ms/item); `prefers-reduced-motion` respeitado em tudo.
- **Estados**: hover/active(`scale(0.98)`)/focus-visible ring 2px/disabled/loading por primitivo.
- **Acessibilidade**: contraste AA nos textos, alvo de toque ≥44px em mobile, skip-to-content.

## 4. Fases

### Fase 0 — Fundação (~½ dia)
1. Instalar deps: `npm i @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-tooltip @radix-ui/react-tabs @radix-ui/react-select lucide-react sonner framer-motion clsx tailwind-merge`.
2. Criar `frontend/DESIGN.md` completo conforme seção 3 (+ Research Log: referências Layer B `linear.app.md` e `supabase.md` lidas como fonte de tokens).
3. Migrar fonte para `next/font/google` (Geist), remover `@import` do globals.css.
4. Refatorar `tailwind.config.js`: cores semânticas (background/surface/border/accent/muted/semantic-risk) apontando para os tokens; manter aliases antigos (`primary`, `surface`) temporariamente para não quebrar páginas ainda não migradas.
5. **Aceite**: `tsc --noEmit` limpo; `npm run build` passa; app idêntico visualmente exceto fonte.

### Fase 1 — Biblioteca de primitivos (~1 dia)
Criar em `src/components/ui/`: Button (variants: primary/secondary/ghost/danger × sizes × loading), Input, Textarea, Card, Badge, Dialog (Radix, focus trap), DropdownMenu, Tooltip, Tabs, Select, Skeleton, EmptyState, Toaster (sonner configurado no layout), Spinner.
Migrar `ConfirmDialog`/`AlertBanner` internamente para Radix mantendo as assinaturas públicas (zero mudança nas páginas).
**Gate obrigatório**: página `/design` (rota dev-only) mostrando todos os primitivos + estados; QA visual 375/768/1280 antes de Fase 2.
**Aceite**: `tsc --noEmit` limpo; showcase renderiza sem erros de console.

### Fase 2 — App shell responsivo (~½ dia)
1. Sidebar → componente responsivo: drawer overlay <1024px (hamburger no Header, fecha em navegação/Escape), colapsada fixa ≥1024px; remover `ml-64` fixo do layout.
2. Header honesto: badge backend via polling `/health` (30s, pausa em `document.hidden`) refletindo real estado; breadcrumb completo (mapa cobrindo todas as rotas incl. dinâmicas).
3. Error boundary por rota (`error.tsx` + `not-found.tsx` estilizados); skip-to-content; `100dvh`; container `max-w-[1440px]`.
4. Remover card fake "Sistema operacional" da Sidebar (substituir por versão real ou remover).
**Aceite**: fluxo completo navegável em 375px sem scroll horizontal; status do header reflete backend parado/ativo.

### Fase 3 — Páginas por impacto (~2 dias)
Ordem estrita, uma PR/passo por página, cada uma: trocar emojis/SVGs→Lucide, estados→primitivos, toasts em ações, grid empilhado mobile.
1. **Dashboard** (`page.tsx`): stats cards com tabular-nums, lista de docs, ações com toast feedback.
2. **Analysis** (`analysis/[id]/page.tsx` + `components/analysis/*` + chat): split list/detail que empilha em mobile, ChatPanel como drawer/sheet em mobile, polling mantido.
3. **Report** (`report/[id]/page.tsx` + ScoreGauge/Accordion): gauges SVG mantidos, hierarquia reforçada.
4. **Upload** (`upload/page.tsx` + DropZone).
5. **Comparação** (lista, matriz `[id]`, versões) + **Moldes** + **GerarTR**.
**Aceite por página**: `tsc --noEmit` limpo; zero emoji restante na página; interações principais testadas em 375px.

### Fase 4 — Polimento e verificação final (~1 dia)
1. Motion: staggered entry em listas, spring em drawers/dialogs, spotlight border nos cards hero — apenas onde comunica.
2. Limpeza: remover CSS morto do globals.css sobrando, aliases antigos do tailwind se 100% migrados.
3. **Verificação final (gate)**: `npm run build` exit 0 · Lighthouse ≥95 perf/a11y/best-practices nas rotas Dashboard+Analysis (mobile preset) · QA visual das 9 telas em 375/768/1280 com estados de hover/focus/loading · zero console errors.

## 5. Riscos e Mitigações
- **Regressão funcional**: migrações por página com build+tsc entre cada; assinaturas públicas preservadas.
- **Tailwind v3 vs padrões shadcn v4**: usar sintaxe v3 (HSL vars em `tailwind.config.js`, sem `@theme`).
- **ChatPanel mobile**: virar sheet full-height; testado com teclado virtual (viewport dinâmico → `100dvh`).
- **Cota LLM não afetada**: nada neste plano toca backend.

## 6. Fora de escopo
Autenticação/RBAC, i18n, dark/light toggle (app é dark-only por decisão), migração Tailwind v4, RSC/streaming (páginas permanecem `'use client'`).

---

## 7. Continuação UX SEI / funil (09/09/2026) — CONCLUÍDA

Branch: `feat/ux-sprint2-funil` (sobre `feat/confiabilidade-master`).

| Sprint | Escopo | Status |
|---|---|---|
| 1 P0 | Review humana SEI (`PATCH` + UI), upload auto-start análise, dashboard CTAs/refresh | Feito |
| 2 P1 | Nav longest-prefix + Auditoria, Sheet drawer/chat mobile, abas Comparações, fundir wizard→upload | Feito |
| 3 P2 | Breadcrumbs links, microcopy institucional, EmptyState, migração `btn-primary`→Button | Feito |

Artefatos novos relevantes: `components/ui/Sheet.tsx`, `CorrectionReviewActions.tsx`, `ChatCopilot.tsx`, `useUploadAnalysisPipeline.ts`, `useComparacaoPage.ts`, `tests/test_correction_review_api.py`.
