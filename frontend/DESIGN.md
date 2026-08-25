# DESIGN.md — Contrato de Design LicitAI

> Fonte da verdade visual. Toda cor, fonte, espaçamento e componente no frontend deve rastrear até um token deste arquivo.
> Direção aprovada pelo usuário (25/08/2026): **dark premium refinado**, responsivo completo, stack Radix + Lucide + Sonner + framer-motion.

## 0. Research Log

| Lane | Entregável |
|---|---|
| Referência Layer A (estilo) | `redesign-skill.md` lido na íntegra — workflow audit-first, anti-slop, prioridade de correções |
| Referência Layer B (tokens) | `linear.app.md` lida na íntegra — adotados: modelo de elevação por luminância (não sombras), bordas branco-semitransparentes, texto #F2F5F7 (não branco puro), peso médio como workhorse, tracking negativo em display. **Não copiado**: accent violeta (fingerprint de IA genérica) |
| Shortlist descartada | `supabase.md` — skip: Linear já cobre o sistema completo; accent verde colidiria com semântico de sucesso do produto |
| ui-ux-db / lazyweb / imagen | Não rodadas — projeto existente com identidade dark já definida; auditoria substituiu exploração |

## 1. Tema e Atmosfera

**Direção**: "Sala de situação jurídica" — escuridão como meio nativo, precisão engenharia, um único acento cromático. Conteúdo emerge da superfície escura por graduações de luminância, não por cor.

- **Momento-assinatura**: painel de análise onde o diff DE→PARA é o herói visual — rim light sutil nos cards, acento teal apenas onde há interação/estado.
- **Material base**: superfícies translúcidas com elevação por luminância (0.02 → 0.04 → 0.06 de branco), nunca fundos sólidos claros.
- **Vidro real** = tint de fundo + `backdrop-blur(12px)` + borda 1px semitransparente + **rim light** (`inset 0 1px 0 rgba(255,255,255,0.06)`) + sheen radial opcional no topo.

## 2. Cor

### Tokens semânticos (CSS vars em `:root`, mapeados no tailwind.config)

| Token | Valor | Uso |
|---|---|---|
| `--canvas` | `#0B0E13` | Fundo da página (carvão azulado profundo) |
| `--panel` | `#11151C` | Sidebar, header, superfícies fixas |
| `--surface` | `#171C25` | Cards, dropdowns, modais |
| `--surface-hover` | `#1D232E` | Hover de cards/list items |
| `--border-subtle` | `rgba(255,255,255,0.06)` | Borda padrão |
| `--border-strong` | `rgba(255,255,255,0.10)` | Inputs, divisores destacados |
| `--text-primary` | `#F2F5F7` | Texto principal (nunca `#FFF`) |
| `--text-secondary` | `#C3CBD4` | Corpo de texto |
| `--text-muted` | `#8A93A0` | Metadados, placeholders |
| `--text-subtle` | `#5C6570` | Desabilitado, timestamps |

### Accent único — teal-petróleo (substitui indigo AI-gradient)

Rampa `accent` (HSL ~172°, sat ≤65%): `50 #ECFCF9 · 100 #D0F7F0 · 200 #A3EEE3 · 300 #71DFCF · 400 #43C9B9 · **500 #2AAFA0** · 600 #1F8E83 · 700 #1B7268 · 800 #185B54 · 900 #14453F`

Regras:
- `accent-500` = interação primária (links, botões preenchidos, item ativo, foco)
- `accent-600` = hover de superfícies preenchidas
- **Nunca decorativo** — só comunica interatividade ou estado ativo
- Proibidos: gradientes multi-cor em texto/botões (`text-gradient` removido), glow difuso, segunda cor de marca

### Semânticos de risco (mantidos, mesma família)

`risk-low #22c55e · risk-medium #eab308 · risk-high #f97316 · risk-critical #ef4444`
Badges: sempre fundo `{cor}/10` + texto `{cor}-400` + borda `{cor}/20`. Badge informativo neutro: cinza, não azul.

## 3. Tipografia

| Role | Fonte | Peso | Tracking | Notas |
|---|---|---|---|---|
| Display (h1 página) | Geist Sans | 600 | `-0.03em` | 28–32px desktop / 22px mobile |
| Heading (h2/h3) | Geist Sans | 600/500 | `-0.02em` | 18–20px |
| Body | Geist Sans | 400 | normal | 14–15px, line-height 1.6, máx ~70ch |
| Label/UI | Geist Sans | 500 | `+0.01em` | 12–13px |
| Overline | Geist Sans | 500 | `+0.08em` uppercase | 11px, `text-muted` |
| Números/dados | **Geist Mono** | 400–500 | normal | `tabular-nums` obrigatório: notas, tamanhos, datas, contagens, CNPJ |

Carregada via `geist/font/sans` + `geist/font/mono` (pacote oficial Vercel, variáveis CSS `--font-geist-sans`/`--font-geist-mono`). Proibido `@import` de fonte no CSS.

## 4. Espaçamento, Layout e Breakpoints

- Base 4px; ritmo principal 8/12/16/24/32/48.
- Container: `max-w-[1440px] mx-auto`; leitura de texto ≤70ch.
- Raio: `rounded-md`(6px) inputs/botões · `rounded-lg`(8px) cards · `rounded-xl`(12px) painéis/modais · `rounded-full` pills.
- Breakpoints Tailwind v3: mobile-first. **`lg` (1024px) = limite sidebar fixa vs drawer.**
- Altura: `100dvh` sempre (nunca `h-screen`); alvos de toque ≥44px em mobile.

## 5. Primitivos (`src/components/ui/`) e estados

Todos os primitivos expõem: default · hover · active(`scale-[0.98]`) · focus-visible(ring 2px `accent-500/60` offset 2px) · disabled(`opacity-50 cursor-not-allowed`) · loading(spinner inline).

| Primitivo | Base | Variantes |
|---|---|---|
| `Button` | 36px h (sm 32/md 40/lg 44) | primary(accent-600 sólido) · secondary(branco 4%+borda) · ghost · danger(red-600/15+borda red-500/40) |
| `Input`/`Textarea` | bg branco 3%, borda subtle, focus ring accent | erro: borda red-500/50 + mensagem abaixo |
| `Card` | surface translúcido + border-subtle + rim light | `interactive`: hover luminância +1 passo |
| `Badge` | pill, 11px weight 500 | risk-* · category-* · neutral |
| `Dialog` (Radix) | overlay `rgba(0,0,0,0.7)+blur(4px)`, conteúdo surface, raio xl, sombra dialog | focus trap nativo, Escape, foco no cancelar se danger |
| `DropdownMenu`/`Tooltip`/`Tabs`/`Select` | Radix puro estilizado com tokens | idem estados |
| `Toaster` (sonner) | bottom-right desktop / top mobile, tema dark | success/error/warning/info |
| `Skeleton` | pulso branco 6% | forma do conteúdo real |
| `EmptyState` | ícone Lucide muted + título + descrição + ação | — |
| `Spinner` | SVG animado currentColor | sm(16)/md(20)/lg(28) |

Ícones: **exclusivamente `lucide-react`**, stroke 1.75, tamanhos 16/20/24. Emojis proibidos em UI.

## 6. Motion

- Durações: micro 150ms · padrão 250ms · entrada de tela 400ms. Easing `cubic-bezier(0.32, 0.72, 0, 1)`.
- framer-motion: entradas staggered ≤40ms/item (fade+translateY 8px); drawers/modais com spring (`stiffness 400, damping 40`).
- GPU-only (`transform`/`opacity`). Motion só comunica estado/affordance — zero decoração.
- `prefers-reduced-motion`: tudo instantâneo (mantido do globals.css atual).

## 7. Acessibilidade (restrições vinculantes)

- Contraste AA mínimo para todo texto sobre canvas/surface.
- `focus-visible` visível em TODOS os interativos (gap atual dos botões corrigido nos primitivos).
- Dialogs Radix: focus trap + retorno de foco + `aria-labelledby`.
- Skip-to-content como primeiro elemento do body.
- Ícones decorativos: `aria-hidden`; ações só-ícone: `aria-label`.
- Status dinâmicos: região `aria-live="polite"`.

## 8. Dívida Aceita (explícita)

- Aliases legados `primary`/`surface` no tailwind.config permanecem até Fase 3 completar migração de páginas; remoção só com grep provando zero uso.
- Páginas permanecem `'use client'` (sem RSC/streaming nesta passada).
- Dark-only (sem light mode) por decisão de produto.
- Tailwind v3.4 mantido (migração v4 fora de escopo).
