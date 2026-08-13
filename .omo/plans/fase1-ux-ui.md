# Plano — Fase 1 UX/UI: itens baratos de alto impacto

Baseado na análise crítica do documento do Manus AI (ver sessão de 2026-08-13). Escopo aprovado: os 5 itens baratos de alto impacto. NADA de redesign, biblioteca de UI, ou roadmap de 6 semanas.

## Contexto verificado no código

- Erros chegam crus do backend via `fetchAPI`/`uploadDocument` em `frontend/src/lib/api.ts` (`errorData.detail` → `throw new Error(...)`).
- Status reais do documento: `uploaded | parsing | parsed | analyzing | completed | error` (`STATUS_LABELS` em `frontend/src/types/index.ts:243`); `DocumentDetailResponse` tem `error_message` (types:31).
- `uploadDocument(file, { documentType, fornecedorId })` JÁ aceita tipo TR/Proposta + fornecedor (`api.ts:52-61`); `listFornecedores()` existe (`api.ts:124`).
- 4 usos de `confirm()` nativo: `app/page.tsx:31`, `app/moldes/page.tsx:146`, `app/comparacao/page.tsx:150`, `components/RevisionsTimelineModal.tsx:68`.
- Report tem `scores` (label "Nota Geral" = scores[0], backend `app/api/analysis.py:197`), `risk_level`, `corrections_by_severity`, `total_corrections` — tudo disponível para a síntese.
- Emojis no chat: `ChatPanel.tsx:61 (💬), 85 (🤖), 119 (⚠️)`; `ChatMessage.tsx:44 (📚), 69 (⚠️), 81-89 (👍👎), 94 (✓)`.
- Zero acessibilidade: grep `prefers-reduced-motion|aria-live|role="status"|aria-label` = 0 resultados.
- Progresso do upload é fake: `setInterval` 10→80% (`upload/page.tsx:76-78`).

## Unidades de trabalho (ordem de execução)

### U1 — Componentes base reutilizáveis (`components/ui/`)

**Novo `frontend/src/components/ui/ConfirmDialog.tsx`**
- Props: `{ open, title, message, confirmLabel, cancelLabel?, danger?, onConfirm, onCancel }`.
- `role="alertdialog"` + `aria-modal="true"` + `aria-labelledby`/`aria-describedby`.
- Foco automático no botão de cancelar (ref + `useEffect`); Escape fecha; overlay clicável NÃO fecha (evita perda acidental); `z-50` acima da sidebar.
- Botão de confirmação com classe danger (`bg-red-500/20 text-red-400 border-red-500/40`) quando `danger`.

**Novo `frontend/src/components/ui/AlertBanner.tsx`**
- Props: `{ variant: 'error'|'warning'|'info'|'success', title, children?, action? }`.
- Ícone SVG por variante, `role="alert"` (error) / `role="status"` (info/success); sem emoji.

**Critério de aceite:** `tsc --noEmit` limpo; diálogo navegável por teclado (Tab, Enter, Escape).

### U2 — Erros problema + causa + correção

**Novo `frontend/src/lib/errors.ts`**
- `getErrorMessage(err: unknown, ctx: ErrorContext): { title: string; message: string }` com `ErrorContext = 'upload' | 'analysis' | 'documents' | 'chat'`.
- Formato SEMPRE `problema + causa + correção`, ex.:
  - upload: "Não foi possível processar este arquivo. Envie PDF, DOCX ou ODT com até 50 MB. Verifique o arquivo e tente novamente."
  - documentos/lista: "Não foi possível carregar seus documentos. O backend pode estar offline. Verifique se o servidor está rodando em 127.0.0.1:8000 e recarregue."
  - análise timeout/cota: "A análise demorou mais que o esperado. A cota gratuita do provedor de IA pode ter esgotado. Aguarde alguns minutos e tente novamente."
- Mapear mensagens conhecidas do backend (`detail`) quando baterem; fallback genérico no formato acima. Não criar catálogo exaustivo.

**Integrações (substituir blocos de erro por `<AlertBanner>`):**
- `app/page.tsx:104-108` → `variant="error"` com mensagem de ctx `'documents'`.
- `app/upload/page.tsx:231-241` → ctx `'upload'`.
- `app/analysis/[id]/page.tsx:287-315` (banner de análise interrompida + erro de requisição) → ctx `'analysis'`.
- `app/report/[id]/page.tsx:137-143` → manter estrutura, trocar por AlertBanner.
- `components/chat/ChatPanel.tsx:116-129` → ctx `'chat'`.

**Critério de aceite:** nenhum emoji novo; toda mensagem de erro visível ao usuário segue problema+causa+correção; erro do backend desconhecido cai no fallback com o formato.

### U3 — Síntese de score acionável no relatório

**`app/report/[id]/page.tsx`** (após card de gauges, linha ~184)
- Linha de síntese dentro do card "Pontuação": `6,8/10 — risco médio, com 3 achados críticos e 7 recomendações no total`.
- Fonte: `scores[0]` (label "Nota Geral") quando existir; `risk_level` (RISK_LABELS); `corrections_by_severity.critico`/`.alto`; `total_corrections`.
- Tratamento de nulos: score nulo → "Análise sem pontuação — consulte o parecer final."
- Cor do texto segue `getRiskColor(risk_level)` existente.

**Critério de aceite:** frase gerada corretamente com relatório sem score, sem correções e com correções; `tsc` limpo.

### U4 — Upload com etapas reais + tipo TR/Proposta + fornecedor

**`app/upload/page.tsx`**
1. Remover o `setInterval` fake de progresso (linhas 76-78) e o redirecionamento cego de 1.5s.
2. Após `uploadDocument` OK: manter `setState('processing')` e iniciar polling `getDocument(result.id)` a cada 1s.
3. Mapear status do documento para etapas reais (substituir "Processando documento..."):
   - `uploaded` → "Enviando arquivo..."
   - `parsing` → "Extraindo texto e estrutura do documento..."
   - `analyzing` → "Análise em andamento..."
   - `parsed` | `completed` → redirecionar para `/analysis/{id}`.
   - `error` → AlertBanner (U2, ctx upload) usando `doc.error_message` + botão "Tentar Novamente" (reset).
4. Timeout de segurança: interromper polling após 5 min com mensagem orientando a verificar a lista de documentos no Painel.
5. Tipo de documento: `select` com "Termo de Referência" (padrão) / "Proposta de fornecedor". Quando "Proposta": carregar `listFornecedores()` e exibir select de fornecedor (obrigatório nesse caso; mensagem de validação amigável).
6. Passar `uploadDocument(file, { documentType, fornecedorId })`.

**Critério de aceite:** o progresso reflete status reais do backend (sem intervalo fake); upload de proposta envia `document_type=proposta` e `fornecedor_id`; sem tipo TR não envia campos extras (backward compatible).

### U5 — Chat institucional: emojis → ícones SVG

**`components/chat/ChatPanel.tsx`**
- `:61` 💬 → ícone SVG chat/botão de mensagem.
- `:85` 🤖 → ícone SVG bot/assistente no empty state.
- `:119` ⚠️ → ícone SVG alert-triangle.

**`components/chat/ChatMessage.tsx`**
- `:44` 📚 → remover emoji (badge "Ancorado" mantém texto, sem ícone) OU ícone book-open de 12px; escolher UMA opção, manter consistente.
- `:69` ⚠️ (warning) → ícone SVG alert-triangle 12px.
- `:81-89` 👍/👎 → SVGs thumbs up/down.
- `:94` ✓ → SVG check.
- Badges de provedor/confiança/latência: MANTER na fase 1 (mover para painel "Detalhes" é fase 2).

**Critério de aceite:** zero emojis nos componentes de chat; ícones SVG de 12-16px alinhados com `currentColor`/`text-gray-500`.

### U6 — Acessibilidade barata (motion + live regions)

**`app/globals.css`** — ao final:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Live regions** (`aria-live`):
- `app/page.tsx`: wrapper da lista/estatísticas com `aria-live="polite"` (estados loading/erro).
- `app/upload/page.tsx`: região de progresso com `aria-live="polite"`.
- `app/analysis/[id]/page.tsx`: card de progresso da análise (linha ~237) com `role="status"`.

**Critério de aceite:** `prefers-reduced-motion` ativo desativa pulse/shimmer/slide/fade; leitor de tela anuncia mudança de status do upload e da análise.

## Verificação (gates de cada unidade e do conjunto)

1. `cd frontend && npx tsc --noEmit` — zero erros.
2. `cd frontend && npm run lint` — zero erros novos.
3. `cd frontend && npm run build` — exit 0.
4. Teste manual no navegador (fluxo completo): upload (TR e Proposta) → etapas reais → análise → relatório com síntese → chat sem emojis; exclusão de documento com ConfirmDialog via teclado (Tab/Enter/Escape); erro de upload (arquivo grande) com mensagem problema+causa+correção.

## Fora de escopo (fases posteriores)

- Central de trabalho na home; redesign da análise em 3 zonas; relatório executivo; prompts iniciais no chat; painel "Detalhes da resposta" (provedor/latência); sidebar responsiva/agrupada; ToastProvider; DataTable; PageHeader; copiar com "desfazer".

## Riscos

- **Polling do upload:** se o parsing backend for síncrono ao POST, o status já virá `parsed/completed` no 1º GET — o polling cobre ambos; manter 1s de intervalo e 5 min de timeout.
- **Erro de cota da IA (429):** já tratado por mensagem orientativa em U2; não adicionar retry automático (fora de escopo).
- **Badge "Ancorado" sem ícone:** decisão de consistência (texto apenas) — padrão: badges têm texto, ícones são reservados para ações e estados.
