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

- **Frontend**: Next.js 14 (App Router), React 18, Tailwind CSS v3 (Tema escuro premium com Glassmorphism, badges de risco/categoria/agentes e animações), TypeScript.
  - **Proxy Rewrites (`next.config.js`)**: Redirecionamento dinâmico de `/api/*` via `BACKEND_URL` (padrão `http://127.0.0.1:8000` no modo nativo e `http://backend:8000` no Docker).
- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.0 (Async com `asyncpg` e `aiosqlite`), Pydantic v2.
- **Banco de Dados (Duplo Suporte)**:
  - **Produção/Docker**: PostgreSQL 16 com extensão `pgvector` e `uuid-ossp` (preparado para RAG).
  - **Modo Nativo (Windows sem Docker)**: SQLite Async com `aiosqlite` (`licitacao.db` criado automaticamente sem dependência da BIOS/Docker).
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
  - **Google Gemini API** (`gemini_provider.py`) — *Provedor*: `gemini-2.0-flash`.
  - **Groq API** (`groq_provider.py`) — *Provedor ativo*: `llama-3.1-8b-instant` (otimizado para inferência rápida e cota de 500.000 tokens/dia no free tier).
  - **Ollama** (`ollama_provider.py`) — *Local*: `qwen3:32b`, `deepseek-r1:32b`, etc.
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
  - Frontend: `hooks/useChat.ts`, `components/chat/{ChatPanel,ChatMessage,ChatInput,CitationList}.tsx`, integrado em `analysis/[id]/page.tsx` (contexto `page:analysis`, `document_id`, `analysis_id`, `item_number`).
  - Settings em `config.py`: `chat_enabled`, `chat_require_grounding`, `chat_top_k_sources`, `chat_max_message_length`, `chat_max_sources_stored`, `chat_force_fake_provider`.
  - Tabelas `chat_conversations`/`chat_messages` em `db/init.sql` + migração `db/migrations/20260806_add_chat.sql`; contrato validado no `test_init_sql.py` (+4 testes).
- **Qualidade da análise (Fase 2)**:
  - Checklist dos 10 elementos obrigatórios do Art. 6º, XXIII embutido no `SYSTEM_PROMPT`; o `ITEM_ANALYSIS_PROMPT` instrui a sinalizar ausência como correção `juridica`/`estrutural` sem reescrever por conta própria.
  - Revisão cruzada das correções pelo LLM (`services/analyzer/review.py`): segunda passagem aprova/rejeita/ajusta; rejeitadas saem do conjunto de pontuação; ajustadas recebem texto/fundamento novos; falha de revisão mantém correções como `pendente`. Status persistido em `corrections` (`review_status`/`review_note`/`reviewed_at`) e exposto na API.
  - Benchmark de qualidade (`scripts/benchmark.py` + `scripts/benchmark_fixtures.py`): análise + revisão reais com retry/backoff para rate limit; métricas recall/precisão/F1 por TR e por item; relatório em `backend/benchmark_report.json`.
- **RF04 — Feedback/e-mail por fornecedor (Fase 3)**:
  - `services/comparator/feedback.py`: `montar_pendencias` (agrega `falha`/`atencao` por fornecedor, ignora `ok`) + `formatar_email_pendencias` (texto PT-BR com regra, rótulo, esperado/proposto).
  - `services/email/sender.py`: `enviar_email` via smtplib em `asyncio.to_thread` (não bloqueia o loop), `smtp_configurado()` (exige `SMTP_HOST` + `SMTP_FROM`), `EmailConfigError`.
  - Endpoint `POST /comparison/{comparacao_id}/feedback`: 404 se comparação não encontrada; 400 se status ≠ `completed` ou SMTP ausente; retorna `{enviados, falhas[{fornecedor_id, nome, email?, motivo}], fornecedores_sem_pendencias, fornecedores_sem_email}`. Falhas de envio não propagam erro.
  - Config SMTP por env (`config.py` + `.env.example`): `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`.
  - Frontend: formulário de fornecedor com CNPJ/e-mail + edição/exclusão (`comparacao/page.tsx`); botão **Enviar Pendências** nas comparações concluídas; `api.ts` com `updateFornecedor`/`deleteFornecedor`/`enviarFeedback`.

---

## 3. Mapeamento de Arquivos da Aplicação

### Raiz
- `docker-compose.yml`: Orquestração de 3 containers (`db`, `backend`, `frontend`).
- `.env`: Configurações de ambiente (`DATABASE_URL`, `LLM_PROVIDER`, `GROQ_API_KEY`, `POSTGRES_PASSWORD`).
- `.env.example`: Template de configuração.
- `README.md`: Guia completo de instalação, segurança e arquitetura.
- `memory.md`: Memória contínua do projeto.
- `PLANO.md`: Plano do backlog pendente — fases priorizadas (hardening, qualidade, RF04, RAG v1.0, polimentos, v2.0) com tarefas, esforço e critérios de aceite.
- `db/init.sql`: Script de criação das extensões, tabelas (`documents`, `document_items`, `analyses`, `corrections`, `fornecedores`, `moldes`, `comparacoes`, `comparacao_resultados`), índices e triggers no PostgreSQL.
- `e2e/`: Diretório de testes End-to-End com fixtures, scripts e testes.
  - `fixtures/sample-tr.docx`: DOCX de exemplo gerado manualmente (estrutura OPC) para testes.
  - `scripts/generate_fixture.py`: Gera o fixture DOCX (cria ZIP com estrutura OPC válida).
  - `scripts/init_test_db.py`: Inicializa banco SQLite isolado para testes E2E.
  - `.env.test`: Configuração de ambiente para testes (rate limit alto).
  - `run_e2e.ps1`: Script automatizado para execução dos testes E2E.
  - `tests/test_e2e_full_flow.py`: 17 testes E2E cobrindo health check, upload, CRUD, análise e relatório.
  - `tests/conftest.py`: Fixtures Pytest (client HTTP, fixture DOCX, documento com análise).

### Backend (`/backend`)
- `Dockerfile`: Imagem Python 3.12-slim com `tesseract-ocr`, `tesseract-ocr-por` e `libmagic1`.
- `requirements.txt`: Dependências do Python (FastAPI, SQLAlchemy, PyMuPDF, pdfplumber, python-docx, groq, google-genai, aiosqlite, python-magic-bin, etc.).
- `scripts/seed_moldes.py`: Seed idempotente de moldes padrão (TR geral, serviços continuados, obras públicas).
- `scripts/download_laws.py` e `scripts/ingest_laws.py`: Corpus jurídico (Lei 14.133 + 13.303).
- `scripts/migrate_review_columns.py`: Migração idempotente (SQLite/PostgreSQL) das colunas `review_status`/`review_note`/`reviewed_at` na tabela `corrections`.
- `scripts/benchmark.py` + `scripts/benchmark_fixtures.py`: Benchmark de qualidade da análise (recall/precisão/F1) com TRs fixture e LLM real; grava `benchmark_report.json`.
- `tests/`: Testes unitários (loader, extractor, comparator, matrix, llm_timeout, `test_analyzer.py` — checklist Art. 6º + revisão cruzada com providers fake; `test_feedback.py` — agregação de pendências, formatação e guarda SMTP; `test_feedback_api.py` — integração do endpoint com banco SQLite em memória + `enviar_email` mockado; `test_chat_validator.py` — grounding/recusa/JSON do Copiloto; `test_chat_api.py` — integração `/api/v1/chat` com fake LLM).
- `app/main.py`: Aplicação FastAPI, middlewares de segurança (CSP, CORS allowlist, Rate Limit) e health check.
- `app/config.py`: Validação de variáveis de ambiente com Pydantic Settings (`extra="ignore"` habilitado). Inclui campos SMTP (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM`) da RF04.
- `app/database.py`: Conexão assíncrona SQLAlchemy (suporta `postgresql+asyncpg` e `sqlite+aiosqlite`).
- `app/models/`:
  - `document.py`: Modelos ORM `Document` e `DocumentItem` (com `document_type` e `fornecedor_id`).
  - `analysis.py`: Modelos ORM `Analysis` e `Correction` (com colunas de revisão `review_status`/`review_note`/`reviewed_at`).
  - `comparison.py`: Modelos ORM `Fornecedor`, `Molde`, `Comparacao` e `ComparacaoResultado`.
  - `chat.py`: Modelos ORM `ChatConversation` e `ChatMessage` (PK `int` autoincrement, `sources`/`context_json` JSON, `grounded`/`confidence`/`provider`/`latency_ms`, `feedback_rating`/`feedback_comment`).
- `app/schemas/`:
  - `document.py`: Schemas Pydantic de requisição e resposta de documentos.
  - `analysis.py`: Schemas Pydantic de análises, correções e relatórios (`CorrectionResponse` expõe `review_status`/`review_note`/`reviewed_at`).
  - `comparison.py`: Schemas de fornecedores, moldes, comparação e matriz de conformidade.
  - `chat.py`: Schemas do Copiloto (`ChatConversationCreate`, `ChatMessageCreate` com limite de tamanho via settings, `ChatFeedbackCreate`, `ChatCitation`, `ChatConversationResponse`, `ChatMessageResponse`, `ChatHealthResponse`).
- `app/api/`:
  - `router.py`: Router `/api/v1`.
  - `documents.py`: Endpoints `/documents/upload`, `/documents/`, `/documents/{id}` e DELETE (upload aceita `document_type` + `fornecedor_id`).
  - `analysis.py`: Endpoints `/analysis/{document_id}/start` (Background Task), `/analysis/{analysis_id}`, `/analysis/{analysis_id}/report`.
  - `rules.py`: CRUD de moldes (`/moldes` POST/GET/PUT/DELETE) com validação do `config_json` e delete protegido por integridade (409 se houver comparações).
  - `fornecedores.py`: CRUD de fornecedores (`/fornecedores`) com delete protegido (409 se houver propostas).
  - `comparison.py`: `/comparison/start` (Background Task), `/comparison` (lista), `/comparison/{id}`, `/comparison/{id}/matrix`.
  - `chat.py`: Endpoints `/chat/health`, `/chat/conversations`, `/chat/conversations/{id}/messages`, `/chat/messages/{id}/feedback`.
- `app/services/parser/`:
  - `pdf_parser.py`: PyMuPDF primário -> pdfplumber fallback (tabelas) -> Tesseract OCR.
  - `docx_parser.py`: Extração via `python-docx` com detecção de estilos e tabelas.
  - `structurer.py`: Regex para extração da árvore de itens numerados e anexos.
- `app/services/llm/`:
  - `provider.py`: Classe abstrata `LLMProvider` e factory `get_llm_provider()`.
  - `groq_provider.py`, `gemini_provider.py`, `ollama_provider.py`: Implementações dos provedores.
- `app/services/analyzer/`:
  - `prompts.py`: Persona do Especialista Sênior, regras estritas, checklist do Art. 6º XXIII, prompts de análise e de revisão cruzada.
  - `engine.py`: Motor de execução da análise item a item + revisão cruzada pós-análise + pontuação global.
  - `review.py`: Revisão cruzada das correções pelo LLM (aprova/rejeita/ajusta) — Fase 2.2.
  - `report.py`: Gerador de relatórios em Markdown formatado.
- `app/services/rules/` (Auditoria RF02):
  - `loader.py`: Schema Pydantic do `config_json` (tipos: numero_inteiro, numero_extenso, booleano, legal, data, percentual, monetario) + validação.
  - `extractor.py`: Extração determinística de valores por âncora (numérica, extensa, booleana, legal, data ISO, percentual, monetária).
  - `llm_fallback.py`: Fallback LLM via `get_llm_provider()` real — sem mock.
- `app/services/comparator/` (Auditoria RF03 + RF04):
  - `comparator.py`: `comparar_regra()` classifica OK/FALHA/ATENÇÃO; `comparar()` executa regras × propostas.
  - `matrix.py`: `montar_matriz()` organiza regras (linhas) × fornecedores (colunas).
  - `feedback.py`: `montar_pendencias()` agrega `falha`/`atencao` por fornecedor (ignora `ok`); `formatar_email_pendencias()` monta texto PT-BR.
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
- `next.config.js`: Proxy rewrites dinâmicos apontando para `BACKEND_URL` (`http://127.0.0.1:8000`).
- `package.json`: Next.js 14, React 18, Tailwind CSS v3.
- `src/types/index.ts`: Mapeamento TypeScript dos schemas da API, tipos de âncora (`AnchorTipo`, `RegraConfig`, `MoldeConfig`) e rótulos amigáveis em PT-BR.
- `src/lib/api.ts`: Cliente HTTP para chamadas assíncronas ao backend (inclui `getMolde`, `updateMolde`, `deleteMolde`, `updateFornecedor`, `deleteFornecedor`, `enviarFeedback`).
- `src/app/`:
  - `globals.css`: Estilos globais, glassmorphism e estilização de diffs DE/PARA.
  - `layout.tsx`: Layout raiz com `Sidebar` e `Header`.
  - `page.tsx`: Dashboard (resumo de métricas, lista de documentos enviados, status e ações).
  - `upload/page.tsx`: Tela de upload com drag-and-drop, indicador de progresso e validação client-side.
  - `analysis/[id]/page.tsx`: Tela principal de análise com ações em 1-clique para cópia rápida ao SEI:
    - `Copiar Texto Corrigido (PARA)`
    - `Copiar Item Inteiro para o SEI` (substituição automática do texto original pelo corrigido)
    - `Copiar Justificativa & Fundamentação Legal`
  - `report/[id]/page.tsx`: Relatório consolidado com gauges SVG de nota (0-10), gráficos de barras de distribuição por categoria/severidade, botão `Copiar Parecer para o SEI` e acordeão de correções com atalhos de cópia.
  - `comparacao/page.tsx`: Listagem de comparações + criação (seleção de TR, molde e propostas) + cadastro de fornecedor + upload de proposta vinculado.
  - `comparacao/[id]/page.tsx`: Matriz de conformidade regras × fornecedores com polling a cada 3s durante execução.
  - `moldes/page.tsx`: Editor visual de moldes de regras (cria/edita regras com campos dinâmicos por tipo de âncora, preview do JSON, delete protegido).
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

- **PRD Executável v2.0 (Correções de Alto Impacto) — fases A–D e validação E concluídas (05/08/2026)**:
  - **Fase A (Parsing)**: títulos de seção determinísticos via sha256+NFC (`T-{digest%100000}` — sem `hash()`); alíneas (`a)`, `b)`) detectadas como subitem e itens romanos (`I.`, `II.`) como seção. **+3 testes**.
  - **Fase B (Extração por regras)**: `_texto_por_ancora` usa a partir da 1ª ocorrência; regex de inteiro ignora número de item e milhar monetário; monetário sem `_para_decimal`; datas inválidas rejeitadas (`datetime.date`); CNPJ valida dígitos verificadores (módulo 11); números por extenso compostos ("vinte e um"→21). **+10 testes**; fixture `test_fase4_fase5` corrigida para CNPJ com DV válido (`-95`).
  - **Fase C (RAG)**: FTS5 com `remove_diacritics 2` (busca sem acento); retrieval híbrido RRF (semântico + textual com try/except); warn de dimensão de embedding; cache LRU 256 de query-embeddings. **+2 testes**.
  - **Fase D (Banco)**: `db/init.sql` sincronizado com os models (corrigido `);` faltante em `document_items`, `items_snapshot JSON`, `analysis_mode`, `agent_origin`, `embedding TEXT`, removido ivfflat); constraint `uq_comparacao_fornecedor_regra`; script `dedupe_comparacao_resultados.py`; paginação `page`/`page_size` em documents/fornecedores/comparison (backward-compatible; `analysis.py` sem paginação — frontend espera lista crua).
  - **Fase E (Validação)**: corpus reingerido no banco real (**7 documentos, 315 chunks, 100% com embedding**); benchmark sem regressão; `db/init.sql` validado via parser oficial do PostgreSQL (**12 testes `test_init_sql.py`**).
- **Suíte de Testes**: **156 testes unitários passando** (0 falhas) + **17 E2E** (13 passed; 4 erros de timeout do fixture de análise aguardando LLM real sob cota diária esgotada — ambientais, janela ajustada 60s→240s).
- **Copiloto LicitAI (chat consultivo) implementado (06/08/2026)**: módulo backend isolado + API `/api/v1/chat` + frontend integrado na tela de análise; **26 novos testes** (11 validator + 16 API incl. guards) + **4 testes de schema** (`test_init_sql.py` chat contract). Smoke test real validado com `chat_force_fake_provider=True` (health, conversa, mensagem com fonte, feedback, 404/400).
- **Backend FastAPI**: modo nativo Windows (SQLite), provedor ativo **gemini** (`gemini-2.0-flash`), failover Groq. Chaves reais no `.env` da raiz — `config.py` lê `.env` relativo ao CWD (rodar de `backend\` não vê o `.env` da raiz).
- **Frontend Next.js Rodando Ativamente**: `http://localhost:3000`.
- **Banco de Dados Nativo**: `licitacao.db` (raiz) com corpus jurídico completo reingerido.
- **Benchmark (05/08/2026)**: recall médio **0,81**, precisão média **0,86**, F1 médio **0,83** (baseline 03/08: 0,68/0,89/0,77) — sem regressão.
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
- `next build` compilado com 0 erros de compilação ou TypeScript.

---

## 6. Como Executar e Continuar o Desenvolvimento

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

## 8. Próximos Passos (Roadmap para Próximos Agentes)

> Ver `PLANO.md` para o plano completo do backlog. Fases 1 (hardening), 2 (qualidade),
> 3 (RF04 feedback/e-mail), 4 (RAG v1.0), 5 (polimentos), 7 (versionamento) e
> 8 (gerador/extensão) concluídas. PRD executável v2.0 (correções A–D + validação E)
> concluído em **05/08/2026**. **Copiloto LicitAI (PRD v1.1) implementado em 06/08/2026.**

- **Copiloto LicitAI — evoluções futuras (06/08/2026)**:
  - Rodar chat com **LLM real** (remover `chat_force_fake_provider`) para validar o prompt/validator com Gemini/Groq quando a cota diária permitir.
  - Aplicar `suggested_actions` do LLM em versões futuras (hoje descartadas por design — chat é somente-leitura).
  - Listagem de conversas no frontend (`listChatConversations`/`getChatMessages` já existem na API) e retomar conversa existente por `analysis_id`/`document_id`.
  - Considerar `chat_conversations.document_id`/`analysis_id` como FK real (hoje são soft references `VARCHAR(36)` por compatibilidade SQLite/Postgres).
- **Pendências ambientais (05/08/2026)**:
  - Rodar os **4 testes E2E de análise** com cota LLM disponível (Gemini/Groq resetarem) para confirmar 17/17.
  - **Validação de runtime do `db/init.sql` em Postgres real** via `docker compose up -d db` quando houver Docker daemon (hoje validado por parser oficial `pglast` — 12 testes em `tests/test_init_sql.py`). Nota: em volume novo, o `init.sql` é aplicado automaticamente no 1º boot; verificar `document_items` (crítico: `);` corrigido), `analysis_mode`, `agent_origin`, `embedding TEXT`, `uq_comparacao_fornecedor_regra` e ausência de ivfflat.
  - `data/juristcu/` não existe no repo — só `data/rilc/amostra.txt`; `ingest_corpus_extra.py` ingere apenas o que existir. Considerar adicionar acórdãos TCU reais.
- **v2.0**:
  - Múltiplos agentes especializados utilizando LangGraph (Agente Jurídico, Agente Técnico, Agente de Redação, Agente Revisor).
  - Autenticação e controle de acesso (RBAC).
  - Executar os scripts de ingestão **sequencialmente** (execução paralela contra o mesmo SQLite pode causar corrida no rebuild do FTS).

> **Benchmark (05/08/2026)**: recall médio **0,81** · precisão média **0,86** · F1 médio **0,83** (melhoria vs 03/08: 0,68/0,89/0,77 — recall subiu com a calibração do agente estrutural). Recall baixo no TR de "omissões graves" segue como maior lacuna; reavaliar redação do checklist/instruções quando revisitado.
