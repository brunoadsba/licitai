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
- **Provedores de LLM (Factory Pattern)**:
  - **Google Gemini API** (`gemini_provider.py`) — *Provedor ativo*: `gemini-2.0-flash`.
  - **Groq API** (`groq_provider.py`) — *Failover*: `llama-3.3-70b-versatile`.
  - **Ollama** (`ollama_provider.py`) — *Local*: `qwen3:32b`, `deepseek-r1:32b`, etc.
  - Failover automático entre provedores reais (sem mock; exige chave de API válida).
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
- `tests/`: Testes unitários (loader, extractor, comparator, matrix, llm_timeout, `test_analyzer.py` — checklist Art. 6º + revisão cruzada com providers fake; `test_feedback.py` — agregação de pendências, formatação e guarda SMTP; `test_feedback_api.py` — integração do endpoint com banco SQLite em memória + `enviar_email` mockado).
- `app/main.py`: Aplicação FastAPI, middlewares de segurança (CSP, CORS allowlist, Rate Limit) e health check.
- `app/config.py`: Validação de variáveis de ambiente com Pydantic Settings (`extra="ignore"` habilitado). Inclui campos SMTP (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM`) da RF04.
- `app/database.py`: Conexão assíncrona SQLAlchemy (suporta `postgresql+asyncpg` e `sqlite+aiosqlite`).
- `app/models/`:
  - `document.py`: Modelos ORM `Document` e `DocumentItem` (com `document_type` e `fornecedor_id`).
  - `analysis.py`: Modelos ORM `Analysis` e `Correction` (com colunas de revisão `review_status`/`review_note`/`reviewed_at`).
  - `comparison.py`: Modelos ORM `Fornecedor`, `Molde`, `Comparacao` e `ComparacaoResultado`.
- `app/schemas/`:
  - `document.py`: Schemas Pydantic de requisição e resposta de documentos.
  - `analysis.py`: Schemas Pydantic de análises, correções e relatórios (`CorrectionResponse` expõe `review_status`/`review_note`/`reviewed_at`).
  - `comparison.py`: Schemas de fornecedores, moldes, comparação e matriz de conformidade.
- `app/api/`:
  - `router.py`: Router `/api/v1`.
  - `documents.py`: Endpoints `/documents/upload`, `/documents/`, `/documents/{id}` e DELETE (upload aceita `document_type` + `fornecedor_id`).
  - `analysis.py`: Endpoints `/analysis/{document_id}/start` (Background Task), `/analysis/{analysis_id}`, `/analysis/{analysis_id}/report`.
  - `rules.py`: CRUD de moldes (`/moldes` POST/GET/PUT/DELETE) com validação do `config_json` e delete protegido por integridade (409 se houver comparações).
  - `fornecedores.py`: CRUD de fornecedores (`/fornecedores`) com delete protegido (409 se houver propostas).
  - `comparison.py`: `/comparison/start` (Background Task), `/comparison` (lista), `/comparison/{id}`, `/comparison/{id}/matrix`.
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

- **Backend FastAPI Rodando Ativamente**: O servidor FastAPI está em execução em **http://127.0.0.1:8000** (Health Check `/health` respondendo `{"status": "ok", "provider": "gemini"}`). Logging em JSON estruturado. Reiniciado em **03/08** após queda dos processos (ver lição na seção 7).
- **Frontend Next.js Rodando Ativamente**: O servidor Next.js está em execução em **http://localhost:3000** (proxy API redirecionando perfeitamente para `http://127.0.0.1:8000/api/*`). Reiniciado em **03/08** (mesma causa).
- **Banco de Dados Nativo**: O banco SQLite (`licitacao.db`) está inicializado com todas as tabelas criadas, incluindo as do módulo de auditoria (`fornecedores`, `moldes`, `comparacoes`, `comparacao_resultados`).
- **Módulo de Auditoria TR × Propostas (RF02/RF03) implementado**:
  - CRUD de fornecedores e moldes (config_json validado por Pydantic)
  - Upload com `document_type=tr|proposta` + `fornecedor_id`
  - Extração determinística por âncoras (inclui data/percentual/monetário) + fallback LLM real (sem mock)
  - Comparação em BackgroundTasks + matriz de conformidade
  - 40 testes unitários passando (loader, extractor, comparator, matrix) + 17 E2E
  - Frontend: `/comparacao` (listagem/criação), `/comparacao/[id]` (matriz com polling) e `/moldes` (editor visual)
  - Seed de moldes padrão executado (3 moldes) + 1 legado "Molde Padrao TR" = **4 moldes no banco**
  - Delete protegido por integridade (409) validado via API (molde com comparação vinculada → 409)
  - Fluxo E2E dos novos tipos validado (criação via API aceitou data/percentual/monetario; comparação completou com matriz; dados de teste removidos depois)
  - `db/init.sql` atualizado; migração SQLite aplicada (`document_type`/`fornecedor_id` em `documents`)
- **Hardening (Fase 1) implementado**: timeout LLM configurável (`LLM_TIMEOUT_SECONDS`, teste de timeout no FailoverProvider) + logging JSON estruturado — 43 testes unitários passando (loader, extractor, comparator, matrix, llm_timeout) + 17 E2E.
- **Qualidade da análise (Fase 2) implementada**:
  - Checklist dos 10 elementos do Art. 6º, XXIII no prompt (sinaliza ausência sem reescrever)
  - Revisão cruzada das correções pelo LLM integrada ao `engine.py` (`_run_cross_review` pós-análise); status de revisão persistido nas colunas novas de `corrections` (migração SQLite aplicada e idempotente)
  - **52 testes unitários passando** (acrescentados `test_analyzer.py` com providers fake + checklist; +9)
  - **Benchmark executado com LLM real** (Gemini/Groq): recall médio **0,68**, precisão média **0,89**, F1 médio **0,77** — relatório em `backend/benchmark_report.json`
- **RF04 feedback/e-mail (Fase 3) implementada**:
  - `services/comparator/feedback.py` + `services/email/sender.py` (smtplib em `asyncio.to_thread`), config SMTP por env, endpoint `POST /comparison/{id}/feedback` (guards 404/400, resposta parcial com `falhas`)
  - Frontend: formulário de fornecedor com CNPJ/e-mail + edição/exclusão; botão **Enviar Pendências** nas comparações concluídas
  - **67 testes unitários passando** (acrescentados `test_feedback.py`, +7, `test_feedback_api.py` — integração do endpoint com banco em memória e `enviar_email` mockado, +5, e testes de regressão do comparador, +3); `next build` passou com typecheck; backend e frontend rodando (smoke test OK)
  - SMTP de produção **não configurado** (por design): endpoint retorna 400 com mensagem clara até que `SMTP_HOST`/`SMTP_FROM` sejam definidos
- **Ajustes finos pós-Fase 3 (auditoria sênior)**:
  - `comparator.py: _normalizar_numero` corrigido (antes mutilava floats: `str(4.5)`→`"45"`; funcionava só porque ambos os lados eram mutilados igualmente). Agora trata `int/float` direto e strings BR; testes de regressão int×float, colisão decimal e string pt-BR.
  - `comparison.py` refatorado: extraídos `_carregar_fornecedores`, `_fornecedores_ordenados` e `_resultados_para_dict` — removida a duplicação 3x do carregamento de fornecedores e 2x da conversão de resultados.
- **Arquitetura de Múltiplos Agentes Inteligentes (Multi-Agent System) implementada**:
  - `BaseSpecializedAgent` + 4 agentes especializados: `LegalAgent` (⚖️ Jurídico), `TechnicalAgent` (🛠️ Técnico), `WritingAgent` (✍️ Redação) e `StructuralAgent` (📐 Estrutural).
  - `MultiAgentOrchestrator`: executa análises paralelas via `asyncio.gather`, deduplica achados e insere a tag `agent_origin`.
  - Migração SQL executada idempotente (`agent_origin` em `corrections` e `analysis_mode` em `analyses`).
  - Frontend: `types/index.ts`, `api.ts` (suporte ao campo `mode`), `upload/page.tsx` (seletor de modo) e `analysis/[id]/page.tsx` (badges coloridos por agente responsável).
- **RAG v1.0 & Busca Semântica por Embeddings (Fase 4) implementado**:
  - Generator de embeddings (`scripts/ingest_embeddings.py`) usando Gemini/Ollama (`bge-m3`).
  - Ingestão de jurisprudência do TCU (Súmulas 247, 272, Acórdão 1214/2013) e RILC CODEBA (`scripts/ingest_juris_tcu.py`) com 315 chunks no índice FTS5/Semântico.
  - Diff de versões de TR (`services/comparator/diff.py`), endpoint `POST /documents/diff` e interface visual `/comparacao/versoes`.
- **Polimentos no Módulo de Auditoria (Fase 5) implementados**:
  - Extratores de âncoras para **CNPJ** (com validação), **Prazo Relativo** (ex: "30 dias") e **CEP** (`#####-###`).
  - Endpoint de duplicação de moldes `POST /moldes/{id}/duplicate` + botão em 1-clique.
  - Endpoint dry-run `POST /moldes/{id}/validate/{document_id}` + modal de teste em tempo real no frontend.
- **Histórico e Versionamento de Edições Single-User & Agente Estrutural (Fase 7) implementados**:
  - **Uso Estritamente Single-User**: O sistema opera em modo de uso individual (sem necessidade de login JWT ou regras de RBAC).
  - **Histórico e Versionamento de Edições (Single-User)**: Tabela e modelo `DocumentRevision`, endpoints REST `/documents/{id}/revisions` (`POST/GET/RESTORE`) e interface visual `RevisionsTimelineModal.tsx` na tela de análise.
  - **Calibração do Agente Estrutural (`StructuralAgent`)**: Prompt aprimorado com checklist estrito dos 10 incisos do Art. 6º, XXIII da Lei 14.133/21 para elevação do recall na detecção de omissões.
- **Suíte de Testes**: **97 testes unitários passando** (100% no Pytest, incluindo `test_fase7_revisions.py`) + **17 testes E2E passando**.
- `next build` compilado com 0 erros de compilação ou TypeScript (8 páginas geradas com sucesso).

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

## 8. Próximos Passos (Roadmap para Próximos Agentes)

> Ver `PLANO.md` para o plano completo do backlog (fases priorizadas, esforço e critérios de aceite). Fases 1 (hardening), 2 (qualidade da análise) e 3 (RF04 feedback/e-mail) concluídas.

- **Fase 4 — RAG v1.0** (próxima): embeddings/pgvector, JurisTCU + RILC, diff entre versões do TR.
- **Fase 5 — Auditoria (polimentos)**: mais tipos de âncora; duplicar molde; validar molde contra documento.
- **v2.0**:
  - Múltiplos agentes especializados utilizando LangGraph (Agente Jurídico, Agente Técnico, Agente de Redação, Agente Revisor).
  - Autenticação e controle de acesso (RBAC).

> **Benchmark (03/08)**: recall médio 0,68 · precisão média 0,89 · F1 médio 0,77. Recall baixo no TR de "omissões graves" (0,375) — detector de elementos ausentes do Art. 6º é a maior lacuna; reavaliar redação do checklist/instruções quando a Fase 2 for revisitada.
