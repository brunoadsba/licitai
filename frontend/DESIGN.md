# DESIGN.md — Contrato de Design LicitAI

> Fonte da verdade visual. Toda cor, fonte, espaçamento e componente no frontend deve rastrear até um token deste arquivo.
> Atualizado 10/09/2026: **tema claro + escuro** CODEBA (teal `#3AA4A4`), stack Radix + Lucide + Sonner + framer-motion + ThemeProvider.

## 0. Research Log

| Lane | Entregável |
|---|---|
| Referência Layer A (estilo) | `redesign-skill.md` lido na íntegra — workflow audit-first, anti-slop, prioridade de correções |
| Referência Layer B (tokens) | `linear.app.md` lida na íntegra — adotados: modelo de elevação por luminância (não sombras), bordas branco-semitransparentes, texto #F2F5F7 (não branco puro), peso médio como workhorse, tracking negativo em display. **Não copiado**: accent violeta (fingerprint de IA genérica) |
| Shortlist descartada | `supabase.md` — skip: Linear já cobre o sistema completo; accent verde colidiria com semântico de sucesso do produto |
| ui-ux-db / lazyweb / imagen | Não rodadas — projeto existente com identidade dark já definida; auditoria substituiu exploração |

## 1. Tema e Atmosfera

**Direção**: claro + escuro com a mesma identidade CODEBA (teal + navy). Toggle no header; preferência em `localStorage` (`licitai-theme`).

- **Escuro**: ink `#06080F` / graphite surfaces / teal luminoso.
- **Claro**: canvas `#F3F6FB` (azul-acinzentado frio, sem cream) / panel branco / texto slate / accent teal `#247070`–`#3AA4A4`.
- Classes: `html.light` | `html.dark` (`darkMode: 'class'` no Tailwind).
- FOUC: script inline no `<head>` antes da hidratação.

## 2. Cor — derivada da identidade CODEBA

Paleta extraída de `Logo CODEBA.png`:
- **Navy CODEBA** `#051853` — wash atmosférico / selo
- **Azul CODEBA** `#0355CF` — pontual
- **Teal CODEBA** `#3AA4A4` — **accent-500** (interativo)
- **Cinza Autoridade** `#606163`

### Tokens semânticos

Valores abaixo = **escuro** (`html.dark`). No **claro** (`html.light` / `:root`): canvas `#F3F6FB`, panel/surface `#FFFFFF`, textos slate (`#0F172A`…`#94A3B8`), bordas `rgba(15,23,42,…)`. Ver `globals.css`.

| Token | Escuro | Uso |
|---|---|---|
| `--canvas` | `#06080F` | Fundo da página |
| `--panel` | `#0A0F18` | Sidebar, header |
| `--surface` | `#111827` | Cards, dropdowns, modais |
| `--surface-hover` | `#1A2436` | Hover |
| `--border-subtle` | `rgba(148,163,184,0.10)` | Borda padrão |
| `--border-strong` | `rgba(148,163,184,0.16)` | Inputs |
| `--text-primary` | `#F1F5F9` | Texto principal |
| `--text-secondary` | `#CBD5E1` | Corpo |
| `--text-muted` | `#94A3B8` | Metadados |
| `--text-subtle` | `#64748B` | Desabilitado |
| `--codeba-navy` | `#051853` | Wash / selo |
| `--codeba-teal` | `#3AA4A4` | Accent |

### Tema claro/escuro (código)

- `ThemeProvider` + `ThemeToggle` em `frontend/src/components/theme/`
- Preferência: `localStorage['licitai-theme']` = `light` \| `dark`
- Script anti-FOUC no `<head>` do `layout.tsx`
- Toaster (Sonner) acompanha o tema

### Accent único — teal CODEBA `#3AA4A4`

Rampa centrada no teal do logo. Botão primary: gradiente vertical `accent-400 → accent-600` (único matiz, sem multi-cor). Proibidos: roxo/indigo AI, glow difuso exagerado, segunda cor de marca interativa.

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
| `Button` | 36px h (sm 32/md 40/lg 44) | primary(accent-700 sólido, hover accent-800 — contraste AA 5.8:1) · secondary(branco 4%+borda) · ghost · danger(red-600/15+borda red-500/40) |
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

- Aliases legados `primary`/`surface` no tailwind.config permanecem até grep provar zero uso.
- Páginas permanecem `'use client'` (sem RSC/streaming nesta passada).
- Tailwind v3.4 mantido (migração v4 fora de escopo).
- Tema **claro + escuro** entregue (10/09/2026); dívida “dark-only” encerrada.
- Onda UX elaborador (11/09/2026): fluxo Enviar → Revisar agora → SEI; relatório = leitura/print; copiloto sob demanda.
- Redução gradual de `glass-card` no caminho crítico (painel/análise/upload); auditoria avançada ainda usa sheen em pontos.