# Contexto e Memória do Projeto: Sistema Especialista em Análise de TR (SEI)

Este arquivo serve como **fonte da verdade e memória contínua** para qualquer agente de IA ou desenvolvedor dar prosseguimento ao projeto sem perda de contexto.

---

## 1. Visão Geral do Projeto

O **Sistema Especialista em Análise de Termos de Referência (SEI)** é uma aplicação full-stack desenhada para analisar, revisar e aperfeiçoar Termos de Referência (TR) elaborados para licitações públicas (com foco nas Leis 14.133/2021 e 13.303/2016, RILC, TCU, AGU e CGU).

### Principais Objetivos do MVP:
- Upload de documentos em **PDF**, **DOCX** e **ODT**.
- **Parsing e estruturação hierárquica automática** (seções, itens 1.1, subitens 1.1.1, alíneas, cláusulas e anexos).
- **OCR automático com Tesseract** como fallback para PDFs escaneados (sem texto selecionável).
- **Análise item a item via IA em Múltiplos Agentes Inteligentes Especializados**:
  - **⚖️ Agente Jurídico**: Conformidade legal (Lei 14.133/21, Lei 13.303/16, TCU, AGU, CGU).
  - **🛠️ Agente Técnico**: Especificações técnicas, quantitativos, amostragem, SLAs e viabilidade.
  - **✍️ Agente de Redação**: Ambiguidade, clareza, termos subjetivos e ampla competitividade.
  - **📐 Agente Estrutural**: Organização e checklist do Art. 6º, XXIII da Lei 14.133/2021.
  - **👑 Orquestrador Multi-Agente**: Execução concorrente assíncrona (`asyncio.gather`) + deduplicação de achados + etiquetagem com `agent_origin`.
- Sugestões de melhoria fundamentadas no formato **DE → PARA** (com gravidade, risco, justificativa e embasamento legal).
- **RAG v1.0 & Busca Semântica por Embeddings**:
  - Embeddings semânticos com `get_embeddings_provider()` (Gemini / Ollama `bge-m3`).
  - Base jurídica expandida com **Jurisprudência do TCU** (Súmulas 247, 272, Acórdão 1214/2013) e **RILC CODEBA-2023** (315 chunks no índice FTS5/Semântico).
  - **Comparador Visual de Versões de TR** (`/comparacao/versoes`): Alinhamento inteligente por `item_number` classificando itens em `inalterado`, `alterado`, `adicionado`, `removido`.
- **Auditoria TR × Propostas** (módulo aditivo):
  - **Moldes de regras configuráveis** (RF02) com 10 tipos de âncoras (numéricas, por extenso, booleanas, legais, datas, percentuais, monetárias, **CNPJ**, **prazo relativo** e **CEP**).
  - **Editor visual de moldes** (`/moldes`) com botões de **Duplicar Molde** em 1-clique e **Validação Dry-Run** (modal interativo para testar regras contra qualquer TR em tempo real).
  - **Matriz de conformidade** (RF03) comparando o TR com propostas de fornecedores (status OK / ATENÇÃO / FALHA).
  - **Notificação e Feedback a Fornecedores (RF04)**: Agregação de pendências e envio por e-mail via SMTP.

---

## 2. Arquitetura e Decisões de Design

- **Frontend**: Next.js 14 (App Router), React 18, Tailwind CSS v3 (tema dark + design system teal `#2AAFA0`), TypeScript.
  - **BFF**: Route Handler `/api/proxy/*` injeta `API_TOKEN`; rewrites em `next.config.js` para `/api/v1`, `/livez`, `/readyz`, `/health`.
- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.0 (Async), Pydantic v2, Alembic, worker asyncio (`python -m app.worker`).
- **Banco de Dados (Duplo Suporte)**:
  - **Produção/Docker**: PostgreSQL 16 + `pgvector`; schema via Alembic / `db/init.sql`.
  - **Development**: SQLite Async (`create_all` só neste modo); fora de `APP_ENV=development` exige Postgres + `API_TOKEN`.
- **Arquitetura de Múltiplos Agentes Especializados (`services/agents/`)**:
  - `BaseSpecializedAgent`: Interface comum para os agentes `LegalAgent`, `TechnicalAgent`, `WritingAgent`, `StructuralAgent`.
  - `MultiAgentOrchestrator`: Dispara chamadas paralelas aos agentes especializados e deduplica os achados idênticos.
- **RAG v1.0 & Corpus Jurídico (`services/rag/` + `services/embeddings/`)**:
  - Embeddings vetoriais via `GeminiEmbeddingsProvider` / `OllamaEmbeddingsProvider` armazenados na coluna `legal_chunks.embedding`.
  - Ingestão de acórdãos TCU e RILC CODEBA (`ingest_juris_tcu.py`) com reconstrução de índice FTS5.
  - Diff entre versões do TR (`services/comparator/diff.py`) e endpoint `/documents/diff`.
- **Módulo de Auditoria TR × Propostas & Polimentos**:
  - **Novos Extratores**: CNPJ (dígitos verificadores), Prazo Relativo (ex: "30 dias"), CEP (`#####-###`).
  - **Duplicação & Dry-Run**: Endpoints `POST /moldes/{id}/duplicate` e `POST /moldes/{id}/validate/{document_id}` com modal no frontend.
- **Provedores de LLM (Factory Pattern com Failover Simétrico)**:
  - **Google Gemini API** (`gemini_provider.py`) — *Provedor*: `gemini-flash-latest` (alias estável; `gemini-2.0-flash` descontinuado em 09/09/2026).
  - **Groq API** (`groq_provider.py`) — *Provedor ativo*: `openai/gpt-oss-20b` (`llama-3.1-8b-instant` removido do catálogo Groq em 09/09/2026).
  - **Ollama** (`ollama_provider.py`) — *Local*: `qwen3:32b`, `deepseek-r1:32b`, `hermes3` (mais leve, bom em JSON/instruções; opção para TRs sigilosos), etc.
  - **Failover Simétrico (`provider.py`)**: Tenta o provedor primário configurado (`LLM_PROVIDER`) e realiza fallback automático para os demais provedores com chaves válidas.
- **Compatibilidade Windows**:
  - `python-magic-bin` instalado para validação de magic bytes sem dependências C externas no Windows.
  - `UPLOAD_DIR` configurado dinamicamente para `./uploads`.
- **Segurança**:
  - Content Security Policy (CSP) restritivo, headers de segurança (X-Frame-Options DENY, X-Content-Type-Options nosniff).
  - Rate limiting in-memory (configurável via env `RATE_LIMIT_MAX`, padrão 600 req/min).
  - Validação rigorosa de uploads (allowlist de extensão + validação por magic bytes).
  - Nomes de arquivos armazenados renomeados para UUIDs (fora do web root).
- **Hardening (Fase 1)**:
  - Timeout por chamada LLM configurável via `LLM_TIMEOUT_SECONDS` (padrão 120s) aplicado com `asyncio.wait_for` no `FailoverProvider.generate` — estouro aciona o fallback.
  - Logging estruturado JSON via `app/utils/logging_config.py` aplicado no `main.py` (sem secrets).
- **Copiloto LicitAI (chat consultivo, 06/08/2026)**:
  - Módulo isolado `backend/app/services/chat/` (`llm_adapter.py`, `sources.py`, `prompts.py`, `validator.py`, `service.py`) + `backend/app/api/chat.py` + `models/chat.py` + `schemas/chat.py`.
  - API `/api/v1/chat`: `GET /health`, `POST /conversations` (201), `GET /conversations` (paginado por `updated_at` desc), `GET /conversations/{id}/messages`, `POST /conversations/{id}/messages`, `POST /messages/{id}/feedback` (400 em role=user, 404 inexistente, 422 rating inválido).
  - **Grounding obrigatório** (`CHAT_REQUIRE_GROUNDING`): resposta factual exige citação válida ou recusa explícita; `suggested_actions` do LLM são **descartadas** no MVP (zero escrita em entidades de negócio).
  - Fake provider determinístico para testes/demo (`CHAT_FORCE_FAKE_PROVIDER`); testes usam `app.dependency_overrides[get_chat_llm]` — nunca LLM real.
  - Recuperação de fontes com **savepoints** (`begin_nested`): falha de consulta (ex: tabela FTS ausente) não envenena a transação da conversa.
  - Frontend: `hooks/useChat.ts`, `components/chat/{ChatCopilot,ChatPanel,ChatMessage,ChatInput,CitationList}.tsx` — desktop docked; mobile FAB+Sheet; integrado em `analysis/[id]/page.tsx` (contexto `page:analysis`, `document_id`, `analysis_id`, `item_number`).
  - Settings em `config.py`: `chat_enabled`, `chat_require_grounding`, `chat_top_k_sources`, `chat_max_message_length`, `chat_max_sources_stored`, `chat_force_fake_provider`.
  - Tabelas `chat_conversations`/`chat_messages` em `db/init.sql` + migração `db/migrations/20260806_add_chat.sql`; contrato validado no `test_init_sql.py` (+4 testes).
- **Qualidade da análise (Fase 2)**:
  - Checklist canônico das **alíneas a–j** do Art. 6º, XXIII (`services/legal/art6_xxiii.py`) — **não** inventar garantia/sanções/cronograma como se fossem o inciso XXIII; prompts/agentes/validador/gerador compartilham a mesma fonte.
  - Revisão cruzada fail-closed das correções (`services/analyzer/review.py`): status/índice inválido não aprova; achados jurídicos altos sem review válida ficam `pendente` e fora do score/cópia SEI.
  - **Revisão humana (09/09)**: `PATCH /api/v1/analysis/corrections/{correction_id}` permite `aprovada|rejeitada|ajustada|pendente` (+ texto/nota em `ajustada`); UI em `CorrectionReviewActions`.
  - Benchmark de qualidade (`scripts/benchmark.py` + `scripts/benchmark_fixtures.py`): análise + revisão reais com retry/backoff para rate limit; métricas recall/precisão/F1 por TR e por item; relatório em `backend/benchmark_report.json`.
  - Golden set local (`e2e/golden/tr_001`…`tr_010`) + FakeLLM determinístico (`analyzer/fake_llm_golden.py`): precision ≥ 0.88 / recall ≥ 0.80 (TP/FP/FN reais; FP deliberado em `tr_010`).
- **Confiabilidade LicitAI — plano mestre implementado (08/09/2026, branch `feat/confiabilidade-master`)**:
  - **Premissas**: single-user; cópia SEI só com `review_status ∈ {aprovada, ajustada}`; auth = BFF Next (`/api/proxy/*`) + `API_TOKEN` server-side (nunca `NEXT_PUBLIC_API_TOKEN`); migrações **Alembic**; jobs = tabela `jobs` no Postgres + worker asyncio (sem Redis).
  - **Schema**: Alembic `20260908_001`…`_003` (`generation_manifest`, `evidence`, `archived_at`, `classification`, `jobs`, `schema_meta`, CHECKs `completed_with_errors` + `file_type=html`); script `scripts/apply_reliability_schema.sql` para Postgres já provisionado; `expected_schema_version` em `config.py` alinhado ao head.
  - **Health**: `/livez` (processo vivo), `/readyz` (DB + schema_version), `/metrics` (in-memory); Compose e Header usam readiness.
  - **Agentes tipados**: `AgentResult` (`ok_empty|findings|failed|parse_error|skipped`); early-exit da fase 2 **somente** se fase 1 concluiu `ok_empty`; cobertura incompleta → status `completed_with_errors` (UI com banner).
  - **Jobs**: `POST .../start` só **enfileira** (sem kick `BackgroundTasks`); processar com `python -m app.worker` ou serviço Compose `worker`. Snapshots em `run_snapshot` / `propostas_ids`.
  - **Restore seguro**: arquiva itens (`archived_at`) e cria novo conjunto — correções não somem por cascade.
  - **Gerador/RAG**: `RetrievedChunk.id` persistido em `rag_chunk_ids`; artefato `file_type=html`.
  - **Privacidade**: `LLM_ALLOW_CLOUD` + classificação `sigiloso` recusam cloud; prompts com `<DOCUMENT_DATA>`; OCR em subprocesso + hard timeout.
  - **Ops docs**: `docs/ops/{deploy,restore-drill,slos}.md`, `backend/scripts/backup.sh`, `scripts/smoke_readyz.sh`, `backend/scripts/promote_feedback.py` (thumbs-down → stub em `e2e/golden/feedback/`).
  - **Testes**: suíte backend **215+** verdes (golden, jobs, OCR, privacy, grounding, reliability P0). CI GitHub permanece **desabilitado** (`ci.yml.disabled`) a pedido do usuário.
  - **Pendência manual (Bruno)**: rotacionar chaves LLM/`POSTGRES_PASSWORD` **depois** (MVP); smoke Compose com worker; backup drill.
- **RF04 — Feedback/e-mail por fornecedor (Fase 3)**:
  - `services/comparator/feedback.py`: `montar_pendencias` (agrega `falha`/`atencao` por fornecedor, ignora `ok`) + `formatar_email_pendencias` (texto PT-BR com regra, rótulo, esperado/proposto).
  - `services/email/sender.py`: `enviar_email` via smtplib em `asyncio.to_thread` (não bloqueia o loop), `smtp_configurado()` (exige `SMTP_HOST` + `SMTP_FROM`), TLS obrigatório quando `smtp_require_tls`, `EmailConfigError`.
  - Endpoint `POST /comparison/{comparacao_id}/feedback`: 404 se comparação não encontrada; 400 se status ≠ `completed` ou SMTP ausente; retorna `{enviados, falhas[{fornecedor_id, nome, email?, motivo}], fornecedores_sem_pendencias, fornecedores_sem_email}`. Falhas de envio não propagam erro.
  - Config SMTP por env (`config.py` + `.env.example`): `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`.
  - Frontend: formulário de fornecedor com CNPJ/e-mail + edição/exclusão (`comparacao/page.tsx`); botão **Enviar Pendências** nas comparações concluídas; `api.ts` com `updateFornecedor`/`deleteFornecedor`/`enviarFeedback`.
- **Refatoração de manutenibilidade (13/08/2026)**:
  - **Backend — extração de módulos de serviço** (commit `047f0ff`): `structurer.py` → `parser/detection.py` + `parser/pagemap.py`; `engine.py` → `analyzer/item_analysis.py` + `analyzer/scoring.py`; `app/api/comparison.py` → `comparator/runner.py` + `comparator/serializers.py` (e-mail movido para `comparator/feedback.py`); `retriever.py` → `rag/backends.py` + `rag/semantic.py`; upload orquestrado por `services/upload_service.py`. Revisão ampla de tratamento de exceções em `generator.py`, `review.py`, `comparison.py`, `documents.py`, `feedback.py` e `schemas/comparison.py`. **+3 testes** (`test_engine.py`); suíte total: **159 testes**.
  - **Frontend — extração de componentes de páginas grandes** (commit `032a890`): páginas reduzidas de 300–600 para < 280 LOC, com componentes por domínio em `src/components/{moldes,analysis,report,comparacao,upload,gerar-tr}/` e módulos compartilhados `src/lib/badges.tsx` (badges de categoria/severidade/agente) e `src/lib/useCopy.ts` (feedback de copiar/colar). `tsc --noEmit` limpo após cada extração e no estado final.
- **Auditoria técnica + correções (24/08/2026)**:
  - **Resiliência LLM (`services/llm/provider.py` reescrito)**: `get_llm_provider()` virou **singleton** (`reset_llm_provider()` p/ testes) — estado de failover persiste entre chamadas; retry único com backoff (1s) para erros transitórios; **timeout não é re-tentado**; **circuit breaker** em 429/quota (cooldown 30s por provedor, `_is_rate_limit_error` detecta 429/RESOURCE_EXHAUSTED/quota/TPM/TPD). Fix: `engine.py` capturava `ValueError` mas a factory levanta `RuntimeError`. Limiter global adicional em `services/llm/limiter.py` (Fase 3 confiabilidade).
  - **Análise paralela (`analyzer/engine.py`)**: pipeline em fases — RAG sequencial (sessão DB única) → análise LLM concorrente com `asyncio.Semaphore(settings.analysis_concurrency, padrão 3)` via `gather(return_exceptions=True)` → persistência sequencial com commit por item → revisão cruzada concorrente (LLM-only) + aplicação sequencial. TR de N itens ≈ 5N+1 chamadas agora com concorrência 3×. Itens com erro não derrubam o lote.
  - **Parsing fora do event loop (`parser/__init__.py`)**: `parse_pdf/docx/odt` (sync, CPU-bound) offloadados via `asyncio.to_thread` — OCR de PDF escaneado não congela mais o backend inteiro durante upload; OCR hard-timeout em subprocesso (`parser/ocr_subprocess.py`).
  - **Docker/env corrigidos**: `docker-compose.yml` com serviços `db`, `backend`, **`worker`**, `frontend`; frontend recebe `BACKEND_URL=http://backend:8000` (também no **build arg** do Dockerfile — rewrites Next embutem no build) e `API_TOKEN` (BFF); default `GROQ_MODEL=openai/gpt-oss-20b`.
  - **Bug de score zero (falsy)**: `api/analysis.py` extraiu `_score_details()` — `float(x) if x is not None` (nota 0.0 legítima não vira mais null); `engine.py` idem (`if analysis.score_overall is None`). Scoring determinístico primário em `analyzer/scoring.py`.
  - **TOCTOU**: `start_analysis` usa `with_for_update()` no Document (serializa starts concorrentes no Postgres; no-op SQLite); `start_comparacao` idem via `db.get(..., with_for_update=True)`.
  - **N+1 eliminado**: `list_comparacoes` pré-carrega fornecedores da página em 1 query (`montar_comparacao_response(c, db, fornecedores_precarregados)`).
  - **Observabilidade**: providers Groq/Gemini/Ollama logam `llm_usage` (prompt/completion/total tokens + latência) e o FailoverProvider loga `llm_call` por chamada; `/metrics` in-memory.
  - **Frontend**: `api.ts` tipado via BFF `/api/proxy/v1` (GET/POST/PUT/PATCH/DELETE); polling com `skipCache`, backoff e pausa em aba oculta (`lib/polling.ts`); cópia SEI só `aprovada|ajustada` (`CorrectionCard`/`ItemDetail`) **após revisão humana** (`PATCH /analysis/corrections/{id}` + UI Aprovar/Rejeitar/Ajustar).
  - **Quick wins**: `main.py` lifespan; `/livez`/`/readyz`/`/health`; warning quando item >8000 chars é truncado.
  - **Tooling**: `backend/pyproject.toml` (ruff); **CI GitHub Actions permanece DESABILITADO** (`ci.yml.disabled`) — não reabilitar sem pedido explícito.
  - **Pendências da auditoria que FORAM feitas na confiabilidade (08/09)**: Alembic (substitui create_all em staging/prod; create_all só SQLite development), fila durável, filtro SEI, checklist Art. 6 correto, agentes tipados. Ainda fora de escopo: multi-tenant/RBAC, LangGraph, fine-tune, K8s.
- **Modernização UX/UI do frontend CONCLUÍDA (25/08/2026 — branch `feat/ux-modernization`)**: 
  - **Plano aprovado pelo usuário** (`.omo/plans/frontend-ux-modernization.md`): dark premium refinado (nível Linear/Supabase), responsivo completo, stack moderna. Auditoria prévia identificou P0s: zero mobile (sidebar fixa 256px), status fake "IA Ativa"/"Sistema operacional" hardcoded, sem toasts, Inter via `@import`, ~30 emojis como ícones + SVGs Heroicons inline duplicados, estética AI-gradient (indigo #6366f1 + glow), botões sem `focus-visible`, breadcrumb quebrado em `/gerar-tr` e `/comparacao/versoes`, sem error boundary.
  - **Fase 0 (concluída)**: `frontend/DESIGN.md` (contrato: tokens semânticos em CSS vars — canvas #0B0E13/panel #11151C/surface #171C25, texto #F2F5F7/#C3CBD4/#8A93A0, **accent único teal-petróleo #2AAFA0 substituindo o indigo**, risco mantido); fonte **Geist Sans/Mono** via pacote `geist` + `next/font` (removido @import); `tailwind.config.js` com tokens semânticos (`accent`, `canvas`, `panel`, `elevated`, `content.*`, `line.*`) **mantendo aliases legados** `primary`/`surface` (agora apontando para o teal) até migração total; deps novas: @radix-ui/*, lucide-react, sonner, framer-motion, clsx, tailwind-merge.
  - **Fase 1 (concluída)**: biblioteca de primitivos `src/components/ui/` — Button (variants/sizes/loading/focus-visible), Input, Textarea, Card, Badge (11 tons), Skeleton, EmptyState, Spinner, Dialog/DropdownMenu/Tooltip/Tabs/Select (Radix), Toaster (sonner montado no layout), ConfirmDialog **migrado para Radix com assinatura pública preservada**; showcase dev-only em `/design` (gate de QA visual 375/768/1280 aprovado).
  - **Fase 2 (concluída)**: shell responsivo — Sidebar com **drawer mobile** (<1024px, hamburger no Header, fecha em navegação/Escape/overlay, `ShellContext`), desktop fixa; Header honesto com **status real do backend** (polling `/readyz` → badge "Backend ativo/offline"; rewrites `/livez`/`/readyz`/`/health` no `next.config.js`) e breadcrumb completo; card fake "Sistema operacional" removido; `error.tsx`/`not-found.tsx` estilizados; skip-to-content; `100dvh`; container `max-w-[1440px]`.
  - **Fase 3a–3d (concluídas)**: Dashboard (stats tabular-nums, EmptyState, toasts sonner), Analysis (grid empilhável `lg:grid-cols-12`, botões Button com loading, Lucide), AnalysisProgress (emojis → ícones Lucide Bot/Scale/Wrench/PenLine/Ruler, aria-progressbar), ItemList/ItemDetail/CorrectionCard (tokens, foco visível, `lib/badges.tsx` com `AGENT_ORIGIN_CONFIG` usando LucideIcon), ChatPanel/ChatInput (altura responsiva `h-[480px] lg:calc`, Button/textarea com tokens), Report (gauges mantidos, parecer com borda accent em vez de glow, tnum), Upload (Radix Select para tipo/fornecedor, DropZone com Lucide, toasts). `tsc --noEmit` limpo após cada fase; commits por fase.
  - **Fase 3e (concluída, `af6dd94`)**: `comparacao/{page, [id]/page, versoes/page}`, `moldes/page` + `MoldeList/MoldeForm/RegraEditor/DryRunModal`, `gerar-tr/{page, PassoDados, PassoRequisitos, ResultadoTR}`, `RevisionsTimelineModal` (migrado para Radix Dialog) e `chat/{ChatMessage, CitationList}` — todos com emojis/SVGs inline → Lucide + primitivos `ui/`, grids empilháveis, toasts em ações; `versoes` e `ResultadoTR` com bug pré-existente `badge-success/warning/danger` corrigido para `badge-baixo/medio/critico`; `gerar-tr` com `alert()` → `toast.success`.
  - **Fase 4 (concluída, `59a4ebd`)**: motion com intenção — `Dialog`/`DropdownMenu`/`Tooltip` com keyframes `overlayIn/contentIn/menuIn` (sem `tailwindcss-animate`), `Dashboard` com stagger `framer-motion` (`MotionConfig reducedMotion="user"`), `Sidebar` drawer com spring (`stiffness 400, damping 40`, `AnimatePresence`); **aliases legados `primary`/`surface` removidos** do `tailwind.config.js` (grep provou zero uso em `.tsx`+`.ts`; único `surface-hover` remanescente é var semântica própria); `.glow` removido do `globals.css`; contraste do botão primário corrigido (`accent-600` 3.99:1 → `accent-700` 5.8:1, Lighthouse `color-contrast` resolvido); ordem de headings corrigida (`EmptyState h3→h2`, `Dashboard li h3→p`, `ItemDetail h3→h2`, `ChatPanel h3→h2`, `Upload h3→h2`, `RevisionsTimelineModal h4→h3`); `tsc` limpo, `next build` ok, **Lighthouse mobile 100/96/100** (a11y 100, best-practices 96 — único falho restante é 8× `Failed to load resource: 500` do proxy com backend offline, ambiental), QA visual **375/768/1280 sem overflow** (7 rotas + 404) e interações (dialog focus trap/Escape, drawer overlay/spring/Escape) verificados; dev server reiniciado (`100dvh`, `.next` preservado).
  - **Nota de ambiente (25/08)**: delegação via subagentes `task()` **indisponível** (billing do workspace opencode — "No payment method"); execução feita diretamente pelo orquestrador com gates por fase (tsc/build/QA visual via Chrome DevTools MCP).
- **UX Sprint SEI / funil (09/09/2026 — branch `feat/ux-sprint2-funil`)**:
  - **Sprint 1 (P0)**: revisão humana de correções — `PATCH /api/v1/analysis/corrections/{correction_id}` (`CorrectionReviewUpdate`), UI Aprovar/Rejeitar/Ajustar (`CorrectionReviewActions`), gate SEI no accordion do relatório, BFF com `PATCH`; upload chama `startAnalysis` pós-parse (`useUploadAnalysisPipeline`); dashboard com CTAs por status, Atualizar + poll leve, cards com `Link`.
  - **Sprint 2 (P1)**: nav longest-prefix + grupo Auditoria; drawer mobile via `Sheet` (Radix focus trap); Copiloto em FAB+sheet no mobile (`ChatCopilot`); Comparações em abas Histórico/Nova/Fornecedores; `/upload` modos Rápido|Avançado; `/wizard` redireciona para `/upload`.
  - **Sprint 3 (P2)**: breadcrumbs clicáveis; microcopy sem localhost/`.env`; EmptyState em listas vazias; `btn-primary` → `Button` nos empties críticos.
  - Testes: `tests/test_correction_review_api.py` (7); `tsc --noEmit` limpo; smoke Docker `:3000`/`:8000`.
- **Polish UI/testes (10/09/2026 — `feat/polish-badges-print-pytest`, mergeado em `feat/confiabilidade-master`)**:
  - Badges unificados: `Badge` + `getCategoryTone`/`getSeverityTone`; classes `.badge-*` removidas do `globals.css`.
  - Relatório: botão **Exportar PDF** (`window.print()`), CSS `@media print` / `.no-print` no shell.
  - `backend/tests/conftest.py` força SQLite async para pytest local independente do `.env`.

---

## 3. Mapeamento de Arquivos da Aplicação

### Raiz
- `docker-compose.yml`: Orquestração de 4 containers (`db`, `backend`, `worker`, `frontend`).
- `.env`: Configurações de ambiente (`DATABASE_URL`, `LLM_PROVIDER`, `GROQ_API_KEY`, `POSTGRES_PASSWORD`, `API_TOKEN`).
- `.env.example`: Template de configuração (BFF usa `API_TOKEN`; sem `NEXT_PUBLIC_API_TOKEN`).
- `README.md`: Guia completo de instalação, segurança e arquitetura.
- `memory.md`: Memória contínua do projeto.
- `PLANO.md`: Plano do backlog pendente — fases priorizadas (hardening, qualidade, RF04, RAG v1.0, polimentos, v2.0) com tarefas, esforço e critérios de aceite.
- `docs/ops/`: Deploy imutável, restore drill, SLOs.
- `scripts/apply_reliability_schema.sql` + `scripts/smoke_readyz.sh`: migrate/smoke Postgres local.
- `db/init.sql`: Script de criação das extensões, tabelas (`documents`, `document_items`, `analyses`, `corrections`, `jobs`, `schema_meta`, `fornecedores`, `moldes`, `comparacoes`, `comparacao_resultados`, chat), índices e triggers no PostgreSQL.
- `e2e/`: Diretório de testes End-to-End com fixtures, scripts e testes.
  - `fixtures/sample-tr.docx`: DOCX de exemplo gerado manualmente (estrutura OPC) para testes.
  - `scripts/generate_fixture.py`: Gera o fixture DOCX (cria ZIP com estrutura OPC válida).
  - `scripts/init_test_db.py`: Inicializa banco SQLite isolado para testes E2E.
  - `.env.test`: Configuração de ambiente para testes (rate limit alto).
  - `run_e2e.ps1`: Script automatizado para execução dos testes E2E.
  - `tests/test_e2e_full_flow.py`: 17 testes E2E cobrindo health check, upload, CRUD, análise e relatório.
  - `tests/conftest.py`: Fixtures Pytest (client HTTP, fixture DOCX, documento com análise).
  - `golden/`: Régua de confiabilidade (≥10 TRs sintéticos + FakeLLM).

### Backend (`/backend`)
- `Dockerfile`: Imagem Python 3.12-slim com `tesseract-ocr`, `tesseract-ocr-por` e `libmagic1`.
- `alembic.ini` + `alembic/versions/`: Migrações de schema (head atual `20260908_003`).
- `requirements.txt` / `requirements-dev.txt`: Dependências runtime e teste (inclui Alembic).
- `app/worker.py`: Worker da fila `jobs` (`python -m app.worker`).
- `scripts/seed_moldes.py`: Seed idempotente de moldes padrão (TR geral, serviços continuados, obras públicas).
- `scripts/download_laws.py` e `scripts/ingest_laws.py`: Corpus jurídico (Lei 14.133 + 13.303).
- `scripts/backup.sh` + `scripts/promote_feedback.py`: Backup Postgres/uploads e promoção de stubs golden.
- `scripts/migrate_review_columns.py`: Migração idempotente (SQLite/PostgreSQL) das colunas `review_status`/`review_note`/`reviewed_at` na tabela `corrections` (legado; preferir Alembic).
- `scripts/benchmark.py` + `scripts/benchmark_fixtures.py`: Benchmark de qualidade da análise (recall/precisão/F1) com TRs fixture e LLM real; grava `benchmark_report.json`.
- `tests/`: Testes unitários (loader, extractor, comparator, matrix, llm_timeout, golden, jobs, OCR, privacy, grounding, reliability P0, chat, feedback).
- `app/main.py`: Aplicação FastAPI, middlewares de segurança (CSP, CORS allowlist, Rate Limit), `/livez`, `/readyz`, `/metrics`, `/health`.
- `app/config.py`: Validação de variáveis de ambiente com Pydantic Settings (`extra="ignore"`, strip CRLF, `APP_ENV` exige `API_TOKEN`+Postgres fora de development).
- `app/database.py`: Conexão assíncrona SQLAlchemy (suporta `postgresql+asyncpg` e `sqlite+aiosqlite`).
- `app/models/`:
  - `document.py`: Modelos ORM `Document` e `DocumentItem` (com `document_type`, `fornecedor_id`, `generation_manifest`, `classification`, `archived_at`).
  - `analysis.py`: Modelos ORM `Analysis` e `Correction` (revisão + `evidence`; status inclui `completed_with_errors`).
  - `job.py`: Fila durável.
  - `comparison.py`: Modelos ORM `Fornecedor`, `Molde`, `Comparacao` e `ComparacaoResultado`.
  - `chat.py`: Modelos ORM `ChatConversation` e `ChatMessage` (PK `int` autoincrement, `sources`/`context_json` JSON, `grounded`/`confidence`/`provider`/`latency_ms`, `feedback_rating`/`feedback_comment`).
- `app/services/legal/art6_xxiii.py`: Checklist canônico Art. 6º XXIII a–j.
- `app/services/jobs/`: enqueue/claim/complete/fail/reclaim.
- `app/schemas/`:
  - `document.py`: Schemas Pydantic de requisição e resposta de documentos.
  - `analysis.py`: Schemas Pydantic de análises, correções e relatórios (`CorrectionResponse` expõe `review_status`/`review_note`/`reviewed_at`).
  - `comparison.py`: Schemas de fornecedores, moldes, comparação e matriz de conformidade.
  - `chat.py`: Schemas do Copiloto (`ChatConversationCreate`, `ChatMessageCreate` com limite de tamanho via settings, `ChatFeedbackCreate`, `ChatCitation`, `ChatConversationResponse`, `ChatMessageResponse`, `ChatHealthResponse`).
- `app/api/`:
  - `router.py`: Router `/api/v1`.
  - `documents.py`: Endpoints `/documents/upload`, `/documents/`, `/documents/{id}` e DELETE (upload aceita `document_type` + `fornecedor_id`).
  - `analysis.py`: `/analysis/{document_id}/start` **só enfileira** job (worker processa); `/sei-corrections`; report; restore arquiva itens.
  - `rules.py`: CRUD de moldes (`/moldes` POST/GET/PUT/DELETE) com validação do `config_json` e delete protegido por integridade (409 se houver comparações).
  - `fornecedores.py`: CRUD de fornecedores (`/fornecedores`) com delete protegido (409 se houver propostas).
  - `comparison.py`: `/comparison/start` **só enfileira**; lista/matrix; feedback SMTP.
  - `chat.py`: Endpoints `/chat/health`, `/chat/conversations`, `/chat/conversations/{id}/messages`, `/chat/messages/{id}/feedback`.
- BFF (token): `frontend/src/app/api/proxy/[...path]/route.ts` — não existe proxy no backend.
- `app/services/parser/`:
  - `pdf_parser.py`: PyMuPDF primário -> pdfplumber fallback (tabelas) -> Tesseract OCR.
  - `docx_parser.py`: Extração via `python-docx` com detecção de estilos e tabelas.
  - `structurer.py`: Regex para extração da árvore de itens numerados e anexos (orquestra `detection.py` + `pagemap.py` desde 13/08).
  - `detection.py`: Detecção de padrões de numeração/seções (extraído de `structurer.py` em 13/08).
  - `pagemap.py`: Mapeamento de texto por página (extraído de `structurer.py` em 13/08).
- `app/services/upload_service.py`: Orquestração de upload de documentos (extraído de `api/documents.py` em 13/08).
- `app/services/rag/`:
  - `retriever.py`: Retrieval híbrido (semântico + FTS5 com RRF) e cache de embeddings (orquestra `backends.py` + `semantic.py` desde 13/08).
  - `backends.py`: Backends de busca textual/semântica (extraído de `retriever.py` em 13/08).
  - `semantic.py`: Busca semântica por embeddings (extraído de `retriever.py` em 13/08).
- `app/services/llm/`:
  - `provider.py`: Classe abstrata `LLMProvider` e factory `get_llm_provider()`.
  - `groq_provider.py`, `gemini_provider.py`, `ollama_provider.py`: Implementações dos provedores.
- `app/services/analyzer/`:
  - `prompts.py`: Persona do Especialista Sênior, regras estritas, checklist do Art. 6º XXIII, prompts de análise e de revisão cruzada.
  - `engine.py`: Motor de execução da análise item a item + revisão cruzada pós-análise + pontuação global (orquestra `item_analysis.py` + `scoring.py` desde 13/08).
  - `item_analysis.py`: Análise individual de um item (extraído de `engine.py` em 13/08).
  - `scoring.py`: Pontuação global e por severidade (extraído de `engine.py` em 13/08).
  - `review.py`: Revisão cruzada das correções pelo LLM (aprova/rejeita/ajusta) — Fase 2.2.
  - `report.py`: Gerador de relatórios em Markdown formatado.
- `app/services/rules/` (Auditoria RF02):
  - `loader.py`: Schema Pydantic do `config_json` (tipos: numero_inteiro, numero_extenso, booleano, legal, data, percentual, monetario) + validação.
  - `extractor.py`: Extração determinística de valores por âncora (numérica, extensa, booleana, legal, data ISO, percentual, monetária).
  - `llm_fallback.py`: Fallback LLM via `get_llm_provider()` real — sem mock.
- `app/services/comparator/` (Auditoria RF03 + RF04):
  - `comparator.py`: `comparar_regra()` classifica OK/FALHA/ATENÇÃO; `comparar()` executa regras × propostas.
  - `matrix.py`: `montar_matriz()` organiza regras (linhas) × fornecedores (colunas).
  - `runner.py`: Execução da comparação em background (extraído de `api/comparison.py` em 13/08).
  - `serializers.py`: Conversão ORM → schemas das comparações (extraído de `api/comparison.py` em 13/08).
  - `feedback.py`: `montar_pendencias()` agrega `falha`/`atencao` por fornecedor (ignora `ok`); `formatar_email_pendencias()` monta texto PT-BR; re-exporta `enviar_email` (moveu de `api/comparison.py` em 13/08).
- `app/services/email/` (RF04):
  - `sender.py`: `smtp_configurado()`, `enviar_email()` (smtplib em `asyncio.to_thread`, texto simples), `EmailConfigError`.
- `app/services/chat/` (Copiloto):
  - `llm_adapter.py`: protocolo `ChatLLMProvider`; `ExistingChatLLM` (usa `get_llm_provider()` com failover) e `FakeChatLLM` (determinístico); factory `get_chat_llm()` respeitando `chat_force_fake_provider`.
  - `sources.py`: `build_sources()` monta citações `legal` (RAG `retrieve`), `analysis`, `correction`, `document_item` — cada recuperação em savepoint (`_seguro`) para não envenenar a transação; dedupe + limite `chat_max_sources_stored`.
  - `prompts.py`: `SYSTEM_PROMPT` exigindo JSON estrito; `build_messages(message, context, fontes)`.
  - `validator.py`: `validate_llm_answer(raw, require_grounding)` → `ValidatedAnswer`; `_extract_json` tolerante a fences; `REFUSAL_MESSAGE`; descarta `suggested_actions`.
  - `service.py`: `send_message()` — fontes → prompt → LLM → validar → persistir user+assistant com `sources/grounded/confidence/provider/model/latency_ms/warning`; erro de LLM → resposta segura com warning (nunca 500).
- `app/utils/`:
  - `file_validation.py`: Validação de extensão, magic bytes, tamanho e caminho seguro (`UPLOAD_DIR`).
  - `security.py`: Middlewares `SecurityHeadersMiddleware` e `RateLimitMiddleware`.
  - `logging_config.py`: Logging estruturado JSON (`JsonFormatter` + `setup_logging`) — sem dados sensíveis.

### Frontend (`/frontend`)
- `DESIGN.md`: **Contrato de design (fonte da verdade visual, 25/08)** — tokens semânticos (canvas/panel/surface, accent teal `#2AAFA0`, content.*, line.*), tipografia Geist, motion, estados, acessibilidade, dívida aceita.
- `next.config.js`: Proxy rewrites `/api/v1`, `/health`, `/livez`, `/readyz` via `BACKEND_URL`; BFF Route Handler em `/api/proxy/*` injeta `API_TOKEN`.
- `package.json`: Next.js 14, React 18, Tailwind CSS v3 + stack UI (@radix-ui/*, lucide-react, sonner, framer-motion, geist, clsx, tailwind-merge) + Playwright (dev).
- `tailwind.config.js`: tokens semânticos (`accent`, `canvas`, `panel`, `elevated`, `content.*`, `line.*`).
- `src/types/index.ts`: Mapeamento TypeScript dos schemas da API e tipos de âncora.
- `src/lib/utils.ts`: `cn()` (clsx + tailwind-merge).
- `src/lib/api.ts`: Cliente HTTP via **BFF** `/api/proxy/v1` (token só no servidor); `skipCache` em polling.
- `src/lib/polling.ts`: Polling com deadline, backoff, limite de falhas, pausa em aba oculta.
- `src/lib/badges.tsx`: `getCategoryTone` / `getSeverityTone` + `AGENT_ORIGIN_CONFIG` (Lucide) — consome o primitivo `Badge` (`tone`).
- `src/lib/useCopy.ts`: Hook `useCopy()` com feedback de cópia (2s).
- `src/components/ui/`: primitivos do design system (Button, Input, Card, Badge, Dialog, Toaster, etc.).
- `src/components/Layout/`: `Sidebar.tsx` (drawer mobile), `Header.tsx` (polling `/readyz`), `ShellContext.tsx`.
- `src/app/api/proxy/[...path]/route.ts`: BFF que encaminha ao backend com `X-API-Token`.
- Rota dev-only `/design`: showcase dos primitivos (gate de QA visual do design system).
- `src/components/` (extração de páginas grandes, 13/08 — páginas < ~280 LOC; **analysis/, report/, upload/ e chat/ migrados para primitivos+Lucide em 25/08**):
  - `moldes/`: `DryRunModal.tsx`, `RegraEditor.tsx`, `MoldeForm.tsx`, `MoldeList.tsx` (pendente migrar 25/08).
  - `analysis/`: `CorrectionCard.tsx`, `ItemList.tsx`, `ItemDetail.tsx` (prop `showCorrections`), `AnalysisProgress.tsx`.
  - `report/`: `ScoreGauge.tsx`, `CorrectionAccordion.tsx`.
  - `comparacao/`: `NovaComparacaoForm.tsx`, `FornecedorPanel.tsx`, `ComparacaoList.tsx` (pendente migrar).
  - `upload/`: `DropZone.tsx` (drag-and-drop com estado interno).
  - `gerar-tr/`: `PassoDados.tsx`, `PassoRequisitos.tsx`, `ResultadoTR.tsx` (pendente migrar).
  - `chat/`: `ChatPanel.tsx`, `ChatMessage.tsx`, `ChatInput.tsx`, `CitationList.tsx` (Panel/Input migrados; Message/CitationList pendentes).
  - `RevisionsTimelineModal.tsx` (pendente migrar — emojis/SVGs inline).
- `src/app/`:
  - `globals.css`: Estilos globais, glassmorphism e estilização de diffs DE/PARA.
  - `layout.tsx`: Layout raiz com `Sidebar` e `Header`.
  - `page.tsx`: Dashboard (resumo de métricas, lista de documentos enviados, status e ações).
  - `upload/page.tsx`: Tela de upload com drag-and-drop (via `DropZone`), indicador de progresso e validação client-side (361→204 LOC).
  - `analysis/[id]/page.tsx`: Tela principal de análise:
    - Cópia SEI **somente** com correções `aprovada`/`ajustada` (badge de `review_status`)
    - Status `completed_with_errors` com banner de cobertura incompleta
    - `Copiar Texto Corrigido (PARA)` / `Copiar Item Inteiro` / justificativa
  - `report/[id]/page.tsx`: Relatório consolidado com gauges SVG, distribuição por categoria/severidade, **Exportar PDF** (`window.print()` + `@media print`), `Copiar Parecer para o SEI` e acordeão de correções.
  - `comparacao/page.tsx`: Listagem de comparações + criação (seleção de TR, molde e propostas) + cadastro de fornecedor + upload de proposta vinculado (542→279 LOC, via `components/comparacao/`).
  - `comparacao/[id]/page.tsx`: Matriz de conformidade regras × fornecedores com polling a cada 3s durante execução.
  - `moldes/page.tsx`: Editor visual de moldes de regras (cria/edita regras com campos dinâmicos por tipo de âncora, preview do JSON, delete protegido) — 592→216 LOC via `components/moldes/`.
  - `gerar-tr/page.tsx`: Geração assistida de TR (304→141 LOC, via `components/gerar-tr/`).
  - `src/hooks/useChat.ts`: Hook do Copiloto (cria conversa, carrega histórico, envia mensagens, feedback up/down).
  - `src/components/chat/`: `ChatPanel.tsx` (painel com header, lista e input), `ChatMessage.tsx` (bolha com badges grounded/confiança/provider/latência e feedback), `ChatInput.tsx` (textarea + Enter), `CitationList.tsx` (acordeão de fontes citadas).

---

## 4. Regras da IA Especialista (`prompts.py`)

A IA atua estritamente sob as seguintes diretrizes:
1. **Nunca**:
   - Alterar texto apenas por estilo ou preferência pessoal.
   - Inventar legislação ou citar leis inexistentes.
   - Criar obrigações que não existem na lei.
   - Reduzir a competitividade da licitação.
   - Alterar o sentido ou objetivo do Termo de Referência.
2. **Sempre**:
   - Justificar cada alteração sugerida com fundamento legal ou técnico (ex: "Art. 40 da Lei 14.133/2021").
   - Informar claramente os riscos da manutenção do texto original.
   - Fornecer saída estritamente formatada em JSON.

---

## 5. Estado Atual do Código

- **Branch ativa (10/09/2026)**: `main` — única branch remota de trabalho; features anteriores (confiabilidade, UX SEI, polish) foram mergeadas via FF. CI permanece desabilitado.
- **Histórico consolidado (08–10/09/2026)**: runtime Docker confiável, modelos LLM atuais, E2E 17/17, UX Sprints 1–3, CSP Next.js, restore drill documentado, unificação `Badge` + Exportar PDF + `backend/tests/conftest.py`.
- **PRD Executável v2.0 (Correções de Alto Impacto) — fases A–D e validação E concluídas (05/08/2026)**:
  - **Fase A (Parsing)**: títulos de seção determinísticos via sha256+NFC (`T-{digest%100000}` — sem `hash()`); alíneas (`a)`, `b)`) detectadas como subitem e itens romanos (`I.`, `II.`) como seção. **+3 testes**.
  - **Fase B (Extração por regras)**: `_texto_por_ancora` usa a partir da 1ª ocorrência; regex de inteiro ignora número de item e milhar monetário; monetário sem `_para_decimal`; datas inválidas rejeitadas (`datetime.date`); CNPJ valida dígitos verificadores (módulo 11); números por extenso compostos ("vinte e um"→21). **+10 testes**; fixture `test_fase4_fase5` corrigida para CNPJ com DV válido (`-95`).
  - **Fase C (RAG)**: FTS5 com `remove_diacritics 2` (busca sem acento); retrieval híbrido RRF (semântico + textual com try/except); warn de dimensão de embedding; cache LRU 256 de query-embeddings. **+2 testes**.
  - **Fase D (Banco)**: `db/init.sql` sincronizado com os models (corrigido `);` faltante em `document_items`, `items_snapshot JSON`, `analysis_mode`, `agent_origin`, `embedding TEXT`, removido ivfflat); constraint `uq_comparacao_fornecedor_regra`; script `dedupe_comparacao_resultados.py`; paginação `page`/`page_size` em documents/fornecedores/comparison (backward-compatible; `analysis.py` sem paginação — frontend espera lista crua). Evolução 08/09: Alembic + `jobs`/`schema_meta`/`archived_at`/CHECKs.
  - **Fase E (Validação)**: corpus reingerido no banco real (**7 documentos, 315 chunks, 100% com embedding**); benchmark sem regressão; `db/init.sql` validado via parser oficial do PostgreSQL (**16 testes `test_init_sql.py`**).
- **Suíte de Testes (08/09)**: **215+ unitários** (golden FakeLLM, jobs, OCR subprocess, privacy, grounding, reliability P0, chat, feedback stub). E2E Playwright smoke existe em `frontend/e2e/` (não é gate CI).
- **Copiloto LicitAI (chat consultivo) implementado (06/08/2026)**: módulo backend isolado + API `/api/v1/chat` + frontend integrado na tela de análise; thumbs-down grava stub em `e2e/golden/feedback/` (promover com `promote_feedback.py`).
- **Backend FastAPI**: provedor configurável (`LLM_PROVIDER`), failover + limiter; fora de `APP_ENV=development` exige `API_TOKEN` e Postgres. Análises/comparações **só avançam com worker**.
- **Modernização UX/UI** na branch `feat/ux-modernization` (25/08) mergeada na linha de confiabilidade; CI permanece desabilitado.
- **Benchmark (05/08/2026)**: recall médio **0,81**, precisão média **0,86**, F1 médio **0,83** (baseline 03/08: 0,68/0,89/0,77). Golden local (08/09) usa FakeLLM com meta precision ≥ 0.88.
- **Módulo de Auditoria TR × Propostas (RF02/RF03) implementado**:
  - CRUD de fornecedores e moldes (config_json validado por Pydantic)
  - Upload com `document_type=tr|proposta` + `fornecedor_id`
  - Extração determinística por âncoras (inclui data/percentual/monetário) + fallback LLM real (sem mock)
  - Comparação em BackgroundTasks + matriz de conformidade
  - Frontend: `/comparacao` (listagem/criação), `/comparacao/[id]` (matriz com polling) e `/moldes` (editor visual)
  - Seed de moldes padrão executado (3 moldes) + 1 legado "Molde Padrao TR" = **4 moldes no banco**
  - Delete protegido por integridade (409) validado via API (molde com comparação vinculada → 409)
- **Hardening (Fase 1) implementado**: timeout LLM configurável (`LLM_TIMEOUT_SECONDS`) + logging JSON estruturado.
- **Qualidade da análise (Fase 2) implementada**: checklist Art. 6º XXIII no prompt + revisão cruzada das correções pelo LLM (status `review_status`/`review_note`/`reviewed_at` persistidos).
- **RF04 feedback/e-mail (Fase 3) implementada**: `feedback.py` + `sender.py` (smtplib em `asyncio.to_thread`); SMTP de produção **não configurado** (por design).
- **Ajustes finos pós-Fase 3**: `_normalizar_numero` do comparador corrigido (mutilava floats); `comparison.py` refatorado (removeu duplicação de carregamento/conversão).
- **Multi-Agent System implementado**: 4 agentes especializados + orquestrador (`asyncio.gather`), tag `agent_origin`, migração idempotente.
- **RAG v1.0 & Busca Semântica (Fase 4) implementado**: `ingest_embeddings.py` (Gemini/Ollama), jurisprudência TCU + RILC, diff de versões `/comparacao/versoes`.
- **Polimentos (Fase 5)**: extratores CNPJ (com validação), Prazo Relativo e CEP; duplicação de molde e dry-run.
- **Fase 7 (Histórico/Versionamento + Agente Estrutural)** e **Fase 8 (Gerador de TR + Extensão SEI + progresso real-time)** implementadas.
- **Correções pré-existentes descobertas na Fase E (05/08/2026)**:
  - `ingest_juris_tcu.py` não chamava `db.commit()` — dados eram descartados ao fechar a sessão (FTS via 315 transientemente, rollback para 310). Corrigido com `await db.commit()`.
  - `ingest_embeddings.py` importava `get_embeddings_provider` de `app.services.embeddings` (inexistente) em vez de `app.services.embeddings.base`. Corrigido.
- **Refatoração de manutenibilidade (13/08/2026, commits `047f0ff` backend + `032a890` frontend)**:
  - **Backend**: `structurer.py` → `detection.py` + `pagemap.py`; `engine.py` → `item_analysis.py` + `scoring.py`; `api/comparison.py` → `comparator/runner.py` + `serializers.py` (email movido p/ `feedback.py`); `retriever.py` → `rag/backends.py` + `semantic.py`; upload → `services/upload_service.py`. Revisão ampla de `except/raise` em generator, review, comparison, documents, feedback e schemas. **159 testes verdes** no venv uv.
  - **Frontend**: 6 páginas grandes extraídas em componentes por domínio — moldes 592→216, analysis/[id] 538→242, report/[id] 419→258, comparacao 542→279, upload 361→204, gerar-tr 304→141 (total 2.756→1.340 LOC). Compartilhados: `src/lib/badges.tsx` + `src/lib/useCopy.ts`. `tsc --noEmit` limpo.
- **Ambiente de desenvolvimento (13/08/2026)**: Python 3.12 do sistema WSL está **corrompido** (`_ctypes` com `undefined symbol: _PyErr_SetLocaleString` — libpython dessincronizada; sem sudo para reparar). Backend roda/valida no venv uv `backend/.venv` (Python 3.13 em cache do uv). **Backend não sobe com o python do sistema** — usar o venv uv.
- `next build` compilado com 0 erros de compilação ou TypeScript.

---

## 6. Como Executar e Continuar o Desenvolvimento

### Ambiente atual (WSL/Linux, 13/08/2026)
> Python 3.12 do sistema **reparado em 13/08** (alinha a stack ao noble 3.12.3 + `python3-pglast` instalado; 159 testes verdes). Tanto o python do sistema quanto o venv uv funcionam:

```bash
# Backend — python do sistema (reparado) ou venv uv (Python 3.13)
cd backend
python3 -m uvicorn app.main:app --reload --app-dir . --host 127.0.0.1 --port 8000   # ou .venv/bin/python
python3 -m pytest tests -q    # 159 passed em ambos

# Frontend
cd frontend
npm run dev
```

### Modo Nativo no Windows (Sem Docker / Sem necessidade de BIOS):
1. **Backend**:
   ```powershell
   backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
   ```
2. **Frontend**:
   ```powershell
   cd frontend
   npm run dev
   ```
3. **Acesse**: http://localhost:3000

### Seed de moldes padrão (opcional, idempotente):
```powershell
$env:PYTHONPATH="backend"
backend\.venv\Scripts\python.exe backend\scripts\seed_moldes.py
```

### Modo Docker (Containers para Produção):
```bash
docker compose up --build
```

### Executar Testes E2E (Requer backend rodando):
```powershell
# 1. Iniciar backend com provedores reais e rate limit ampliado
$env:LLM_PROVIDER="gemini"; $env:RATE_LIMIT_MAX="6000"
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# 2. Rodar testes
$env:E2E_BASE_URL="http://127.0.0.1:8000"; $env:PYTHONPATH="backend"
backend\.venv\Scripts\python.exe -m pytest e2e/tests -v --tb=short

# Ou usar script automatizado:
.\e2e\run_e2e.ps1
```

---

## 7. Bugs e Correções Anteriores

- **Background Task não commitava análise**: O endpoint `POST /analysis/{id}/start` usava `db.flush()` mas não commitava, então a background task (que abre sessão própria) não encontrava o registro da análise. Corrigido com `await db.commit()` antes de agendar a task.
- **Fixture DOCX com magic bytes inválidos**: `python-docx` gerava arquivos detectados como `application/octet-stream` pelo `python-magic-bin` no Windows. A `generate_fixture.py` foi reescrita para construir o ZIP manualmente com estrutura OPC mínima, que é detectada corretamente.
- **Rate limit inflexível**: Era hardcoded em 60 req/min. Adicionado campo `rate_limit_max` no `Settings` do Pydantic (lê de env var), usado pelo middleware.
- **GitGuardian false positive**: O `.env.example` continha valores literais de senha (`CHANGE_ME_TO_A_STRONG_PASSWORD`) que o GitGuardian detectava como "Generic Password". Corrigido substituindo por valores vazios.
- **MissingGreenlet na comparação**: `_run_comparacao_background` acessava `document.items` via lazy loading fora do contexto async, gerando `MissingGreenlet`. Corrigido carregando `Document.items` com `selectinload` nas queries do background.
- **SQLite não expande tuplas em `IN :ids`**: tentativas de DELETE com `IN :tuple` falhavam. Solução: executar em loop com parâmetro único por id.
- **`create_all` não altera tabelas existentes**: ao adicionar `document_type`/`fornecedor_id` à tabela `documents`, foi necessária migração SQL manual (`ALTER TABLE`).
- **Matriz com FornecedorResponse incompleto**: a matriz montava fornecedores só com `{id, nome}`, mas o schema exigia `created_at` etc. Corrigido passando todos os campos.
- **`from_exception_data` exige `ctx.error` string**: ao criar `ValidationError` para JSON inválido no loader de moldes, o tipo `json_invalid` requer `ctx={"error": msg}` (string), não um objeto JSONDecodeError.
- **Delete de molde/fornecedor com dependências**: o SQLAlchemy tentava `SET NULL` nas FKs NOT NULL (molde_id em comparacoes, fornecedor_id em documents), estourando `IntegrityError` no SQLite. Corrigido com guarda de integridade nos endpoints DELETE (retorna `409` quando há comparações/propostas vinculadas).
- **`next build` sobrescreve `.next` do dev server**: rodar build com o dev ativo corrompe o hot reload (MODULE_NOT_FOUND no `_document.js`). Solução: parar o `npm run dev` antes do build e reiniciar depois.
- **UUID em query SQLite**: comparar coluna UUID com string no SQLite falha (`'str' object has no attribute 'hex'`). Usar `uuid.UUID(...)` nos filtros por id em scripts diretos.
- **Logging textual vazava formatação inconsistente**: trocado `logging.basicConfig` textual por `JsonFormatter` (`utils/logging_config.py`). O `json.dumps` não loga `exc_info` como campo vazio — verificada ausência de secrets.
- **Rate limits simultâneos Gemini+Groq**: em horários de pico, Gemini free tier pode zerar a cota diária (429 `RESOURCE_EXHAUSTED`) e Groq estourar TPM ao mesmo tempo. O `FailoverProvider` lida com isso, mas o benchmark travava. Corrigido: `scripts/benchmark.py` ganhou retry/backoff (`_generate_with_retry`, 3 tentativas) + continuidade por item (item com falha não derruba o lote).
- **`string indices must be integers, not 'str'` no benchmark**: `_review_with_retry` retornava a resposta crua do LLM em vez das decisões parseadas — `decisions` era string e `d["correction_index"]` falhava. Corrigido parseando a resposta em `_parse_decisions` (aceita `{"review": [...]}` ou lista direta).
- **`_normalizar_numero` mutilava floats no comparador**: `float(str(4.5).replace(".", "").replace(",", "."))` → `45.0`; os testes passavam porque os dois lados eram mutilados de forma idêntica. Quebrava com mistura int/float e podia colidir casas decimais (12.34 vs 123.4 → ambos `1234`). Corrigido tratando `int/float` diretamente e strings no formato BR (mesma lógica de `extractor._para_decimal`); adicionados testes de regressão.
- **Processos em background morrem com a sessão do shell**: uvicorn (`--reload`) iniciado via `Start-Process` e `npm run dev` caíram juntos (provavelmente quando o terminal pai encerrou). Em **03/08** ambos estavam fora do ar; reiniciados com `Start-Process` (backend: `uvicorn app.main:app --reload` com `LLM_PROVIDER=gemini`, `RATE_LIMIT_MAX=6000`, `PYTHONPATH=backend`, CWD raiz; frontend: `cmd /c npm run dev > npm-dev.log 2>&1` no `frontend/`). Ao retomar o trabalho, sempre checar `/health` e `http://localhost:3000` antes de assumir que estão de pé.
- **`ingest_juris_tcu.py` não commitava os dados (Fase E, 05/08)**: o script iterava `JURISPRUDENCIA_DATA` chamando `ingest_extra_document`/`ingest_law_text` (que fazem `flush`), reconstruía o FTS (via 315 transientemente) e fechava a sessão — **sem `db.commit()`**. SQLAlchemy `async_sessionmaker` sem autocommit descarta tudo no fechamento, então os chunks do TCU/RILC eram perdidos (banco voltava a 310). Corrigido adicionando `await db.commit()` antes do fim do `async with`. Os demais scripts (`ingest_laws.py`, `ingest_corpus_extra.py`) já commitavam — por isso a ingestão das leis funcionava.
- **`ingest_embeddings.py` importava de pacote errado (Fase E, 05/08)**: `from app.services.embeddings import get_embeddings_provider` falhava com `ImportError`, pois a função vive em `app/services/embeddings/base.py` e o `__init__.py` do pacote não a exporta. O `retriever.py` importa corretamente de `app.services.embeddings.base`. Corrigido o import no script.
- **Config `.env` relativo ao CWD (Fase E, 05/08)**: `config.py` usa `SettingsConfigDict(env_file=".env")` que resolve **relativo ao CWD**. Rodar uvicorn/scripts a partir de `backend\` faz o `.env` da raiz ser ignorado → `LLM_PROVIDER` cai no default `groq` com chave vazia → análises falham com "Erro interno durante a análise". Solução (sem alterar código): exportar as variáveis do `.env` da raiz no ambiente do processo antes de executar.
- **Gemini free tier esgota cota diária (05/08)**: `generate_content_free_tier_requests` com `limit: 0` (429) durante o dia após uso intenso (benchmark + E2E). Groq TPD também 99.7k/100k. Impacto: 4 testes E2E de análise falharam por **timeout** (a análise completava, mas além da janela de 60s do fixture). Corrigido aumentando o loop do fixture para 120 iterações × 2s (240s) em `e2e/tests/conftest.py`. Não são regressões de código.
- **Falha de query SQLite envenenava a transação do chat (06/08)**: no Copiloto, `_legal_sources` consulta `legal_chunks_fts` (FTS5). Em banco vazio/in-memory a tabela não existe → `OperationalError`. A exceção era capturada, mas o `commit()` da conversa passava a falhar silenciosamente (mensagens não persistiam). Corrigido executando cada recuperação de fonte dentro de um **savepoint** (`async with db.begin_nested()`) em `_seguro()` — o erro reverte só o savepoint e a transação principal sobrevive.
- **Override de `get_db` em testes precisa commitar (06/08)**: `test_chat_api.py` sobrescreve `get_db` com `async with Session() as s: yield s`, mas o `get_db` real faz `commit()` após o yield. Sem o commit, mensagens persistidas via `flush()` eram perdidas ao fechar a sessão — o teste de persistência falhava. Corrigido replicando o try/commit/rollback do `get_db` real no override.
- **Groq 429 Rate Limit (05/08/2026)**: o modelo `llama-3.3-70b-versatile` no free tier do Groq possui limite de 100k tokens/dia (TPD), que estourou durante o uso do Copiloto. Solução: alterado modelo padrão no `config.py` para `llama-3.1-8b-instant` (cota de 500k tokens/dia no free tier e latência < 1s), tornado o `_build_providers()` simétrico para failover bidirecional (Groq ↔ Gemini) e reiniciado o processo do backend. Teste ao vivo da API confirmou retorno HTTP 200 com resposta válida do Llama.
- **Python 3.12 do sistema WSL corrompido — `_ctypes` quebrado (13/08/2026) — RESOLVIDO**: `import ctypes` falhava com `ImportError: /usr/lib/python3.12/lib-dynload/_ctypes.cpython-312-x86_64-linux-gnu.so: undefined symbol: _PyErr_SetLocaleString`. **Causa raiz (diagnóstico 13/08)**: *mix de fontes apt* — `python3.12-minimal`/`libpython3.12-minimal` eram do **noble (24.04) 3.12.3-1ubuntu0.15**, mas `python3.12`/`python3.12-venv`/`libpython3.12-stdlib` eram do **deadsnakes PPA (build jammy) 3.12.12-1+jammy1** (`deadsnakes-ubuntu-ppa-jammy.sources`). O `_PyErr_SetLocaleString` foi adicionado ao CPython na **3.12.4**; o binário `/usr/bin/python3.12` (noble 3.12.3, `nm -D` sem o símbolo) não o exporta, mas o `_ctypes` 3.12.12 (deadsnakes) o exige. **Reparo aplicado (13/08)**: `sudo apt install --allow-downgrades python3.12=3.12.3-1ubuntu0.15 python3.12-minimal=3.12.3-1ubuntu0.15 libpython3.12-minimal=3.12.3-1ubuntu0.15 libpython3.12-stdlib=3.12.3-1ubuntu0.15 python3.12-venv=3.12.3-1ubuntu0.15` (alinha TODA a stack ao noble — reinstall só dos `-minimal` NÃO resolve, pois o `_ctypes` mora no `-stdlib`) + desabilitado o PPA jammy (`sudo mv /etc/apt/sources.list.d/deadsnakes-ubuntu-ppa-jammy.sources ...disabled`) + `sudo apt install python3-pglast` (faltava no sistema). **Validação**: `import ctypes, magic` ok e **159/159 testes verdes** com o python do sistema.
- **Upload respondia 201 antes do commit (24/08/2026)**: o endpoint `POST /documents/upload` persistia via `flush()` e dependia do commit pós-resposta do `get_db`. Com a resposta chegando ao cliente antes desse commit, um `DELETE`/`GET` imediato sobre o id recém-criado retornava 404 — corrida exposta no E2E (`test_delete_document`) após o parsing virar `asyncio.to_thread` (mudou o timing da janela). Corrigido com `await db.commit()` explícito ao fim do upload; **11/11 E2E não-LLM verdes em 3 runs consecutivas** após o fix.
- **Runtime Docker / modelos LLM (09/09/2026, branch `ops/runtime-confiavel`)**:
  - Frontend standalone embutia `BACKEND_URL=127.0.0.1:8000` no **build** dos rewrites → `/readyz` via UI falhava com `ECONNREFUSED`. Fix: `ARG BACKEND_URL=http://backend:8000` no `frontend/Dockerfile` + `build.args` no Compose; healthcheck do frontend passou a validar `/readyz`.
  - Worker ganhou `--check-db` + healthcheck Compose; smoke `./scripts/smoke_readyz.sh` cobre API, `/api/docs`, frontend e health dos 4 containers.
  - Modelos descontinuados: `llama-3.1-8b-instant` (Groq 404) e `gemini-2.0-flash` (Gemini 404). Defaults atualizados para `openai/gpt-oss-20b` e `gemini-flash-latest`; `ANALYSIS_CONCURRENCY=1` no Compose reduz 429 TPM no free tier.
  - E2E API contra Docker: **17/17** em ~4m22s (`E2E_BASE_URL=http://127.0.0.1:8000`). Fixture de análise em escopo `module` (uma LLM run); aceita `completed_with_errors`; mensagem “enfileirada” alinhada ao worker-only.

## 8. Próximos Passos (Roadmap para Próximos Agentes)

> Ver `PLANO.md` para backlog histórico. Linha ativa: **`main`** (única branch). CI **não** reabilitar sem pedido.

### Agora (ops / Bruno — sem bloquear código)
1. Quando conveniente: rotacionar chaves Gemini/Groq e `POSTGRES_PASSWORD` (adiado no MVP a pedido do usuário).
2. ~~Restore drill~~ — executado 10/09/2026 em staging isolado (`pgvector/pgvector:pg16`); ver `docs/ops/restore-drill.md` (RTO ~3s; backup `licitai_20260910T104546Z`).
3. ~~Merge UX → confiabilidade-master~~ — FF merge em 10/09/2026; CSP incluído.
4. ~~Polish badges/print/pytest~~ — merge FF `feat/polish-badges-print-pytest` → `feat/confiabilidade-master` (10/09).
5. ~~Consolidar em `main`~~ — FF `feat/confiabilidade-master` → `main`; demais branches removidas (10/09).
### Produto / qualidade (não urgente)
- Curadoria humana de stubs em `e2e/golden/feedback/` via `promote_feedback.py` (**0 stubs** em 10/09).
- Playwright live (`E2E_LIVE=1`) opcional.
- Reabilitar CI só se o usuário pedir explicitamente.
- ~~Dualismo badges~~ — unificado em `Badge` + `getCategoryTone`/`getSeverityTone` (10/09).
- ~~PDF export relatório~~ — botão Exportar PDF via `window.print()` + CSS `@media print` (10/09).
- ~~Pytest local review API~~ — `backend/tests/conftest.py` força `sqlite+aiosqlite` antes do import do app (10/09).

### Fora de escopo (premissas travadas)
- Multi-tenant / JWT / RBAC completo; LangGraph; fine-tune; Kubernetes.

> **Benchmark (05/08/2026)**: recall médio **0,81** · precisão média **0,86** · F1 médio **0,83**. Golden FakeLLM (08/09): meta precision ≥ 0.88.  
> **E2E Docker (09/09/2026)**: 17/17 API verdes com Groq `openai/gpt-oss-20b`.  
> **UX SEI (09/09/2026)**: review humana + funil upload/nav/chat/comparação.  
> **Polish (10/09/2026)**: Badge unificado, Exportar PDF do relatório, conftest pytest.  
> **Main única (10/09/2026)**: consolidação FF em `main`; feature branches apagadas.