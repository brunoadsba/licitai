# LicitAI — Sistema Especialista em Análise de Termos de Referência

## 1. Propósito

Sistema full-stack que analisa Termos de Referência (TR) de licitações públicas usando IA, identificando problemas jurídicos, técnicos, de redação e estruturais. Gera correções no formato "DE → PARA" com fundamentação legal, pontuação consolidada (0-10) e parecer final.

Além da análise de correção, o sistema conta com o **módulo de Auditoria TR × Propostas** (aditivo): a partir de moldes de regras configuráveis, compara o TR com as propostas dos fornecedores e gera uma **matriz de conformidade** com status OK / ATENÇÃO / FALHA.

**Público-alvo:** Analistas de licitações, pregoeiros, comissão de contratação, gestores de contratos, advogados públicos, auditores.

## 2. Domínio — Legislação Aplicável

O sistema é especializado nas seguintes normas (em ordem de prioridade):

| Norma | Escopo |
|---|---|
| **Lei 14.133/2021** | Nova Lei de Licitações e Contratos (regime geral) |
| **Lei 13.303/2016** | Lei das Estatais (empresas públicas e S/Es) |
| **Lei 8.666/1993** | Regime anterior (aplicável residualmente) |
| **RILC** | Regulamento Interno de Licitações e Contratos de cada ente |
| **Súmulas TCU** | Jurisprudência consolidada do Tribunal de Contas da União |
| **Orientação AGU/CGU** | Pareceres normativos da Advocacia-Geral da União e Controladoria-Geral |

### Elementos obrigatórios do TR (Art. 6º, XXIII, Lei 14.133/2021):
- Objeto bem definido
- Justificativa da contratação
- Requisitos técnicos
- Modelo de execução
- Modelo de gestão do contrato
- Estimativa de quantidades
- Cronograma físico-financeiro
- Critérios de medição e pagamento
- Sanções administrativas
- Garantias (se aplicável)

## 3. Arquitetura Geral

```
[Frontend Next.js] → API REST → [Backend FastAPI] → [PostgreSQL + pgvector]
                                      ↓
                               [Provedor LLM]
                            (Gemini → Groq)
```

- **Frontend**: Next.js 14 (App Router), React 18, Tailwind CSS v3, tema escuro glassmorphism
- **Backend**: FastAPI + SQLAlchemy 2.0 async + Pydantic v2
- **Banco**: PostgreSQL 16 + pgvector (Docker) ou SQLite + aiosqlite (dev nativo Windows)
- **LLM**: Factory pattern com failover automático (Gemini → Groq)
- **Parser**: PyMuPDF + pdfplumber + Tesseract OCR (PDF), python-docx (DOCX), ZIP+xml (ODT)

## 4. Estrutura de Diretórios

```
licitacao/
├── .env                          # Config ativa (LLM_PROVIDER, chaves de API)
├── .env.example                  # Template (sem segredos)
├── docker-compose.yml            # 3 serviços: db, backend, frontend
├── README.md                     # Guia de instalação
├── memory.md                     # Memória contínua do projeto
├── ideia.md                      # PRD original do projeto
├── explicando-licitai.md         # ← ESTE ARQUIVO (contexto para LLM)
│
├── db/
│   └── init.sql                  # Schema PostgreSQL (tabelas, índices, pgvector)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # Ponto de entrada FastAPI + middlewares
│       ├── config.py             # Settings Pydantic (env vars)
│       ├── database.py           # Engine SQLAlchemy async (SQLite/PostgreSQL)
│       │
│       ├── models/               # ORM SQLAlchemy
│       │   ├── document.py       # Document, DocumentItem
│       │   ├── analysis.py       # Analysis, Correction
│       │   └── comparison.py     # Fornecedor, Molde, Comparacao, ComparacaoResultado
│       │
│       ├── schemas/              # Pydantic (validação entrada/saída)
│       │   ├── document.py       # DocumentCreate, DocumentResponse, DocumentDetailResponse
│       │   ├── analysis.py       # AnalysisResponse, AnalysisDetailResponse, ReportResponse, CorrectionResponse
│       │   └── comparison.py     # Fornecedor, Molde, Comparacao, MatrizResponse, MatrizLinha, MatrizCelula
│       │
│       ├── api/                  # Endpoints REST
│       │   ├── router.py         # Router /api/v1
│       │   ├── documents.py      # POST /upload, GET /, GET /{id}, DELETE /{id}
│       │   ├── analysis.py       # POST /{doc_id}/start, GET /{analysis_id}, GET /{analysis_id}/report
│       │   ├── rules.py          # CRUD /moldes (config_json validado)
│       │   ├── fornecedores.py   # CRUD /fornecedores
│       │   └── comparison.py     # POST /comparison/start, GET /comparison, GET /{id}, GET /{id}/matrix
│       │
│       ├── services/
│       │   ├── parser/           # Extração de texto de documentos
│       │   │   ├── __init__.py   # Dispatch: pdf, docx, odt
│       │   │   ├── pdf_parser.py # PyMuPDF → pdfplumber → Tesseract OCR
│       │   │   ├── docx_parser.py# python-docx
│       │   │   ├── odt_parser.py # ZIP + xml.etree (criado para compliance)
│       │   │   └── structurer.py # Regex → itens hierárquicos (seções, itens, tabelas)
│       │   │
│       │   ├── llm/              # Provedores de IA
│       │   │   ├── provider.py   # ABC + FailoverProvider + factory
│       │   │   ├── gemini_provider.py
│       │   │   ├── groq_provider.py
│       │   │   ├── ollama_provider.py
│       │   │
│       │   ├── analyzer/         # Motor de análise
│       │   │   ├── prompts.py    # System prompt + templates de análise + revisão
│       │   │   ├── engine.py     # Orquestração: análise item a item + RAG + pontuação
│       │   │   ├── json_utils.py # Parsing/validação de respostas JSON do LLM
│       │   │   ├── review.py     # Revisão cruzada das correções (Fase 2.2)
│       │   │   └── report.py     # Geração de relatório Markdown
│       │   │
│       │   ├── rules/            # Módulo de auditoria — moldes de regras (RF02)
│       │   │   ├── loader.py     # Schema Pydantic do config_json + validação
│       │   │   ├── extractor.py  # Extração determinística por âncoras
│       │   │   └── llm_fallback.py  # Fallback LLM (usa get_llm_provider real)│       │   │
│       │   ├── comparator/       # Módulo de auditoria — comparação (RF03)
│       │   │   ├── comparator.py # Classificação determinística OK/FALHA/ATENÇÃO
│       │   │   ├── matrix.py     # Matriz regras × fornecedores
│       │   │   └── feedback.py   # Pendências por fornecedor + texto do e-mail (RF04)
│       │   │
│       │   ├── email/            # RF04 — envio de e-mail
│       │   │   └── sender.py     # smtplib em asyncio.to_thread (SMTP via env)
│       │   │
│       │   └── rag/              # RAG pipeline (IMPLEMENTADO)
│       │       ├── loader.py     # Parser de lei + ingestão no banco + índice FTS5
│       │       └── retriever.py  # Busca FTS5 (SQLite) / ILIKE (PostgreSQL)
│       │
│       └── utils/
│           ├── file_validation.py # Validação de upload (extensão, magic bytes, tamanho)
│           ├── security.py       # Middleware rate limit + security headers
│           └── logging_config.py # Logging estruturado JSON (sem dados sensíveis)
│
├── frontend/
│   ├── package.json
│   ├── next.config.js            # Proxy rewrite /api → backend
│   └── src/
│       ├── types/index.ts        # Interfaces TypeScript (espelham schemas Pydantic)
│       ├── lib/api.ts            # Cliente HTTP
│       └── app/
│           ├── globals.css       # Tema escuro, glassmorphism, badges
│           ├── layout.tsx        # Sidebar + Header
│           ├── page.tsx          # Dashboard
│           ├── upload/page.tsx   # Upload com drag-and-drop
│           ├── analysis/[id]/page.tsx  # Análise item a item com cópia 1-clique
│           ├── report/[id]/page.tsx    # Relatório com gauges e acordeão
│           ├── comparacao/page.tsx     # Listagem + criação de comparação
│           ├── comparacao/[id]/page.tsx  # Matriz de conformidade (polling 3s)
│           └── moldes/page.tsx        # Editor visual de moldes de regras
│
└── e2e/
    ├── .env.test                 # Config para testes (LLM_PROVIDER=gemini)
    ├── scripts/
    │   ├── generate_fixture.py   # Gera DOCX fixture com OPC válido
    │   └── init_test_db.py       # Inicializa banco isolado
    ├── run_e2e.ps1               # Script automatizado
    └── tests/
        ├── conftest.py           # Fixtures (uploaded_document, analyzed_document)
        └── test_e2e_full_flow.py # 17 testes (health, upload, análise, relatório)
```

## 5. Fluxo de Dados (Análise Completa)

```
1. Upload
   Frontend → POST /api/v1/documents/upload (multipart)
   → valida extensão (allowlist)
   → valida magic bytes
   → salva arquivo em ./uploads/{uuid}.{ext}
   → cria registro na tabela documents (status=uploaded)

2. Parsing automático
   → status=parsing
   → parse_document(file_path, file_type)
     → PDF: PyMuPDF → pdfplumber (tabelas) → Tesseract OCR (fallback)
     → DOCX: python-docx (parágrafos + tabelas)
     → ODT: zipfile + xml.etree (parágrafo + tabelas)
   → structure_items(raw_text, pages)
     → regex identifica seções, itens, subitens, alíneas, anexos, tabelas
     → valida duplicatas (renomeia com -1, -2) e conteúdo vazio (ignora)
   → cria registros em document_items
   → status=parsed

3. Análise
   Frontend → POST /api/v1/analysis/{doc_id}/start
   → cria registro em analyses (status=pending)
   → db.commit() (obrigatório para background task enxergar)
   → agendamento em FastAPI BackgroundTasks

4. Background task (run_analysis)
   → status=running
   → Para cada item:
       a. get_llm_provider() → instância com failover
       b. retrieve(db, item.title + item.content, top_k=4) → RAG:
          - SQLite: FTS5 (BM25) sobre legal_chunks
          - PostgreSQL: ILIKE textual (pgvector quando embeddings preenchidos)
       c. ITEM_ANALYSIS_PROMPT.format(item_content[:8000], legal_context)
       d. LLM.generate(system_prompt, user_prompt)
       e. parse_json_response() → extrai JSON de resposta
       f. validate_correction() + sanitize_correction() → normaliza
       g. Salva Correction no banco
   → Gera pontuação via SCORING_PROMPT
   → status=completed (ou error)

5. Relatório
   Frontend → GET /api/v1/analysis/{id}/report
   → Agrega dados da análise, correções por categoria/severidade
   → Gera relatório Markdown (opcional)
```

## 5.1. Fluxo de Dados (Auditoria TR × Propostas)

```
1. Cadastro
   Frontend → POST /api/v1/fornecedores (nome, cnpj, email)
   Frontend → POST /api/v1/moldes (nome + config_json validado pelo loader)

2. Upload de documentos
   POST /api/v1/documents/upload com document_type=tr|proposta
   → TR: document_type=tr (fornecedor_id nulo)
   → Proposta: document_type=proposta + fornecedor_id obrigatório
   → Mesmo pipeline de parsing/estruturação do fluxo anterior

3. Comparação
   Frontend → POST /api/v1/comparison/start
   Body: { tr_document_id, molde_id, propostas_ids: [...] }
   → cria registro em comparacoes (status=pending)
   → db.commit() + BackgroundTasks (mesmo padrão da análise)

4. Background task (_run_comparacao_background)
   → status=running
   → parse_molde(molde.config_json) → regras (id, rotulo, tipo, ancora, ...)
   → Para cada regra:
       a. extrair_valor(regra, itens_do_TR) → valor_tr
       b. Para cada proposta:
          - extrair_valor(regra, itens_da_proposta) → valor_proposta
          - comparar_regra(regra, valor_tr, valor_proposta)
            → status ok | falha | atencao + motivo
   → Salva ComparacaoResultado por (regra, fornecedor)
   → status=completed (ou error com mensagem)

5. Matriz de conformidade
   Frontend → GET /api/v1/comparison/{id}/matrix
   → montar_matriz() → linhas = regras, colunas = fornecedores
   → célula = status + motivo + valor_tr + valor_proposta
```

### Classificação determinística (comparator.py)

| Situação | Status |
|---|---|
| Número igual ao TR (inteiro/extenso/percentual/monetário) | **OK** |
| Número diferente / ausente na proposta | **FALHA** |
| Data igual ao TR (normalizada ISO) | **OK** |
| Data diferente / ausente na proposta | **FALHA** |
| valor_tr não encontrado no TR | **ATENÇÃO** |
| Booleano/legal presente na proposta | **OK** |
| Booleano/legal ausente na proposta | **FALHA** |

Tipos de âncora suportados pelo extrator: `numero_inteiro`, `numero_extenso`, `booleano`, `legal`, `data` (dd/mm/aaaa), `percentual` (ex.: "4,5%"), `monetario` (ex.: "R$ 1.500,00").

O fallback LLM (`rules/llm_fallback.py`) é usado apenas quando a extração determinística não encontra o valor — via `get_llm_provider()` real, sem mock.

## 6. Modelos de Dados (Tabelas)

### documents
| Campo | Tipo | Descrição |
|---|---|---|
| id | UUID | PK |
| filename_original | VARCHAR(500) | Nome original do upload |
| filename_stored | VARCHAR(255) | Nome UUID no filesystem |
| file_type | VARCHAR(10) | 'pdf', 'docx', 'odt' |
| file_size_bytes | BIGINT | > 0 |
| document_type | VARCHAR(10) | 'tr' ou 'proposta' |
| fornecedor_id | UUID | FK → fornecedores (só propostas) |
| total_items | INTEGER | Itens extraídos |
| status | VARCHAR(20) | uploaded, parsing, parsed, analyzing, completed, error |
| error_message | TEXT | Mensagem de erro |
| created_at | TIMESTAMPTZ | UTC |
| updated_at | TIMESTAMPTZ | UTC (trigger auto-update) |

### document_items
| Campo | Tipo | Descrição |
|---|---|---|
| id | UUID | PK |
| document_id | UUID | FK → documents |
| item_number | VARCHAR(50) | "4.3.8", "ANEXO I", etc. |
| title | VARCHAR(500) | Título do item |
| content | TEXT | Texto completo |
| page_number | INTEGER | Página no documento |
| parent_item_id | UUID | FK → document_items (hierarquia) |
| item_order | INTEGER | Ordem no documento |
| item_type | VARCHAR(20) | section, item, subitem, table, annex |

### analyses
| Campo | Tipo | Descrição |
|---|---|---|
| id | UUID | PK |
| document_id | UUID | FK → documents |
| status | VARCHAR(20) | pending, running, completed, error |
| llm_provider | VARCHAR(20) | gemini, groq, ollama |
| llm_model | VARCHAR(100) | Modelo usado |
| total_items / analyzed_items | INTEGER | Progresso |
| score_overall/juridical/technical/writing/structural | NUMERIC(4,2) | 0-10 |
| risk_level | VARCHAR(10) | baixo, medio, alto, critico |
| final_opinion | TEXT | Parecer final |
| created_at / started_at / completed_at | TIMESTAMPTZ | |

### corrections
| Campo | Tipo | Descrição |
|---|---|---|
| id | UUID | PK |
| analysis_id | UUID | FK → analyses |
| document_item_id | UUID | FK → document_items |
| category | VARCHAR(20) | juridica, tecnica, redacao, estrutural |
| severity | VARCHAR(10) | info, baixo, medio, alto, critico |
| situation | TEXT | Situação encontrada |
| problem | TEXT | Problema identificado |
| risk | TEXT | Risco de manter o texto |
| original_text | TEXT | Texto original (DE) |
| suggested_text | TEXT | Texto sugerido (PARA) |
| justification | TEXT | Fundamentação |
| legal_basis | TEXT | Artigos citados |
| importance | VARCHAR(10) | baixa, media, alta, critica |

### legal_chunks (RAG — IMPLEMENTADO)
| Campo | Tipo | Descrição |
|---|---|---|
| id | UUID | PK |
| legal_document_id | UUID | FK → legal_documents |
| chunk_index | INTEGER | Ordem no documento |
| article | VARCHAR(100) | "Art. 6º" |
| section | VARCHAR(200) | Título/capítulo de origem |
| chunk_text | TEXT | Texto integral do artigo (com §§ e incisos) |
| embedding | vector(768) / TEXT | Embedding (PostgreSQL) ou JSON (SQLite) |
| metadata | JSONB / JSON | Lei, título, artigo |

### legal_documents (RAG — IMPLEMENTADO)
| Campo | Tipo | Descrição |
|---|---|---|
| id | UUID | PK |
| law_number | VARCHAR(50) | "Lei 14.133/2021" (único) |
| law_title | VARCHAR(500) | Título da lei |
| source_url | VARCHAR(500) | URL oficial no Planalto |
| version | VARCHAR(50) | Texto consolidado |
| total_chunks | INTEGER | Nº de artigos |
| created_at | TIMESTAMPTZ | UTC |

### fornecedores (Auditoria)
| Campo | Tipo | Descrição |
|---|---|---|
| id | UUID | PK |
| nome | VARCHAR(500) | Nome do fornecedor |
| cnpj | VARCHAR(18) | CNPJ (opcional) |
| email | VARCHAR(255) | E-mail (opcional, futuro RF04) |
| created_at | TIMESTAMPTZ | UTC |

### moldes (Auditoria)
| Campo | Tipo | Descrição |
|---|---|---|
| id | UUID | PK |
| nome | VARCHAR(200) | Nome do molde |
| descricao | TEXT | Descrição |
| config_json | TEXT | JSON validado com as regras |
| created_at | TIMESTAMPTZ | UTC |

### comparacoes (Auditoria)
| Campo | Tipo | Descrição |
|---|---|---|
| id | UUID | PK |
| tr_document_id | UUID | FK → documents (TR) |
| molde_id | UUID | FK → moldes |
| status | VARCHAR(20) | pending, running, completed, error |
| error_message | TEXT | Mensagem de erro |
| created_at / completed_at | TIMESTAMPTZ | |

### comparacao_resultados (Auditoria)
| Campo | Tipo | Descrição |
|---|---|---|
| id | UUID | PK |
| comparacao_id | UUID | FK → comparacoes |
| fornecedor_id | UUID | FK → fornecedores |
| regra_id | VARCHAR(100) | id da regra no molde |
| status | VARCHAR(10) | ok, falha, atencao |
| motivo | TEXT | Explicação da classificação |
| valor_tr | VARCHAR(255) | Valor extraído no TR |
| valor_proposta | VARCHAR(255) | Valor extraído na proposta |
| created_at | TIMESTAMPTZ | UTC |

## 7. Provedores LLM — Failover

Ordem de tentativa conforme `LLM_PROVIDER` no `.env`:

**LLM_PROVIDER=gemini:**
1. Gemini 2.0 Flash (GEMINI_API_KEY)
2. Groq llama-3.3-70b (GROQ_API_KEY)

**LLM_PROVIDER=groq:**
1. Groq llama-3.3-70b (GROQ_API_KEY)
2. Gemini 2.0 Flash (se GEMINI_API_KEY presente)

**LLM_PROVIDER=ollama:**
1. Ollama qwen3:32b (local)

Se nenhum provedor real estiver configurado (chaves ausentes), a inicialização
levanta erro: nenhuma resposta determinística é gerada.

### Parâmetros dos provedores:
- Gemini: temperature=0.3, top_p=0.9, max_output_tokens=4096
- Groq: temperature=0.3, max_tokens=4096

## 8. Sistema de Prompts

### Persona (SYSTEM_PROMPT)
Especialista Sênior em Contratações Públicas (20+ anos). Cobre:
- Lei 14.133/2021, 13.303/2016, 8.666/1993
- Jurisprudência TCU, orientações AGU/CGU, RILC

### Regras obrigatórias:
**NUNCA:**
- Alterar por estilo pessoal
- Inventar legislação
- Criar obrigações inexistentes
- Reduzir competitividade
- Alterar sentido do TR

**SEMPRE:**
- Justificar com fundamento legal
- Citar artigo aplicável (se tiver certeza)
- Informar riscos da manutenção
- Preservar intenção original

### Formato de resposta
JSON array de correções. Array vazio `[]` se item adequado.

### Categorias de análise
1. **Jurídica**: conformidade legal, princípios, riscos de impugnação, direcionamento
2. **Técnica**: objeto, quantitativos, especificações, prazos, fiscalização, garantias
3. **Redação**: clareza, objetividade, ambiguidades, linguagem oficial
4. **Estrutural**: numeração, referências, organização, coerência

## 9. Configuração (.env)

```env
# Obrigatórios para produção:
POSTGRES_PASSWORD=         # Senha do banco PostgreSQL
LLM_PROVIDER=gemini        # gemini | groq | ollama

# Pelo menos uma chave de API:
GEMINI_API_KEY=            # Google AI Studio (free: 1500 req/dia)
GROQ_API_KEY=              # Groq (free: 30 req/min)

# Opcionais:
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/sei_analise
MAX_UPLOAD_SIZE_MB=50
RATE_LIMIT_MAX=600         # Requisições por minuto
ALLOWED_ORIGINS=http://localhost:3000
```

### Modo de desenvolvimento nativo (Windows, sem Docker):
- `DATABASE_URL=sqlite+aiosqlite:///./licitacao.db`
- Backend roda com `uvicorn app.main:app --reload --port 8000`
- Frontend roda com `npm run dev`
- NÃO precisa de PostgreSQL, Docker, WSL, ou BIOS virtualizada

## 10. Regras de Negócio (Validações)

### Upload:
- Extensão permitida: `.pdf`, `.docx`, `.odt`
- MIME types validados por magic bytes (python-magic)
- Tamanho máximo: 50MB (configurável)
- Arquivo renomeado para UUID (nunca usa nome original no filesystem)
- Path traversal prevention

### Parsing:
- Se falhar, document.status = "error", items NÃO são persistidos (rollback implementado)
- Itens com `item_number` duplicado são renomeados com sufixo `-1`, `-2`
- Itens com `content` vazio são ignorados com log warning
- Se nenhum item identificado, cria item único "Documento Completo"

### Análise:
- Conteúdo do item truncado em 8000 caracteres
- LLM provider com failover automático (Gemini → Groq)
- Cada correção é sanitizada: categoria, severidade, importância normalizadas
- Se análise falhar em um item, continua com os próximos
- Pontuação consolidada ao final (se falhar, usa mensagem alternativa)
- Timeout por chamada LLM configurável via `LLM_TIMEOUT_SECONDS` (padrão 120s; estouro aciona failover)

### Auditoria TR × Propostas (RF02/RF03):
- `config_json` do molde validado por schema Pydantic (tipos: `numero_inteiro`, `numero_extenso`, `booleano`, `legal`, `data`, `percentual`, `monetario`)
- ids de regras devem ser únicos; molde exige ao menos 1 regra
- Propostas exigem `fornecedor_id` no upload
- Extração determinística primeiro; fallback LLM (real, sem mock) só para valores não encontrados
- `valor_tr` ausente → status ATENÇÃO (não é possível validar)
- Comparação roda em BackgroundTasks com sessão própria (padrão da análise)
- `Document.items` carregado com `selectinload` no background (evita MissingGreenlet)
- **Delete protegido**: molde com comparações vinculadas e fornecedor com propostas retornam `409` (integridade)
- **Seed de moldes padrão**: `python scripts/seed_moldes.py` (idempotente; TR geral, serviços continuados, obras públicas)

## 11. Diferenciais de UX

- **Cópia 1-clique para o SEI**: botões copiam texto corrigido, justificativa, parecer
- **DE → PARA visual**: diff com cores (vermelho para original, verde para sugerido)
- **Progresso da análise**: barra com % itens analisados
- **Polling automático**: frontend atualiza a cada 3s durante análise
- **Skeleton loading**: feedback visual enquanto carrega
- **Glassmorphism**: tema escuro premium com cards translúcidos

## 12. Estado Atual do Projeto

### Implementado (100% funcional):
- Upload, parsing, estruturação de PDF/DOCX/ODT
- Análise item a item com LLM (Gemini, Groq, Ollama)
- RAG com corpus jurídico: Lei 14.133/2021 (211 artigos) + Lei 13.303/2016 (98 artigos)
  - `backend/data/laws/*.txt` baixados do Planalto (scripts/download_laws.py)
  - Ingestão idempotente via `scripts/ingest_laws.py` (parse por artigo + índice FTS5)
  - Busca FTS5/BM25 no SQLite, ILIKE no PostgreSQL
  - Contexto jurídico injetado no prompt de cada item (top_k=4)
- Geração de relatório com pontuação e parecer
- 17 testes E2E (health, upload, CRUD, análise, relatório)
- Schema com timezone awareness (AwareDatetime)
- Validação de duplicatas e conteúdo vazio no structurer
- Rollback de transação no parser em falha
- GitGuardian limpo (secrets removidos do .env.example)
- Rate limit configurável via env
- Timeout LLM configurável via env (failover aciona em estouro)
- Logging estruturado JSON (sem dados sensíveis)
- Suporte ODT completo
- **Qualidade da análise (Fase 2)**:
  - Checklist dos 10 elementos do Art. 6º, XXIII no prompt (sinaliza ausência sem reescrever)
  - **Revisão cruzada** das correções pelo LLM (`services/analyzer/review.py`): segunda passagem aprova/rejeita/ajusta; status persistido (`review_status`/`review_note`/`reviewed_at`) e exposto na API
  - **Benchmark** (`scripts/benchmark.py` + `benchmark_fixtures.py`): recall/precisão/F1 por TR/item com LLM real (relatório em `backend/benchmark_report.json`)
- **Módulo de Auditoria TR × Propostas (RF02/RF03)**:
  - CRUD de fornecedores e moldes (config_json validado)
  - Upload com `document_type=tr|proposta` + `fornecedor_id`
  - Extração determinística por âncoras (numérica, extensa, booleana, legal, data, percentual, monetária)
  - Fallback LLM via `get_llm_provider()` real (sem mock)
  - Comparação em background (202 + polling) com matriz de conformidade
  - 40 testes unitários (loader, extractor, comparator, matrix)
  - Frontend: página `/comparacao` (listagem/criação) e `/comparacao/[id]` (matriz)
  - **Editor visual de moldes** (`/moldes`): cria/edita regras sem JSON manual
  - **Seed de moldes padrão**: TR geral, serviços continuados e obras públicas
  - **Delete protegido por integridade** (409 para molde/fornecedor com dependências)
  - `db/init.sql` atualizado com as novas tabelas
- **RF04 — Feedback/e-mail por fornecedor (Fase 3)**:
  - Formulário de fornecedor com CNPJ/e-mail + edição/exclusão na UI (`comparacao/page.tsx` + `api.ts`)
  - `services/comparator/feedback.py`: `montar_pendencias` (agrega `falha`/`atencao`, ignora `ok`) e `formatar_email_pendencias`
  - `services/email/sender.py`: `enviar_email` via smtplib em `asyncio.to_thread`, `smtp_configurado()`, `EmailConfigError`
  - Endpoint `POST /comparison/{comparacao_id}/feedback` com guards (404/400) e resposta parcial `{enviados, falhas, ...}`
  - Config SMTP via env (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM`)
  - Botão **Enviar Pendências** nas comparações concluídas com resumo do envio

### Pendente (não iniciado):
- Embeddings semânticos (pgvector preenchido) no PostgreSQL
- Ingestão de JurisTCU (acórdãos TCU) e RILC da CODEBA no corpus
- Autenticação/autorização (MVP single-user)
- Histórico de revisões por documento
- Comparação entre versões do TR
- E-mail HTML rico / anexos no feedback (v1 usa texto simples)

### Bugs conhecidos:
- Nenhum bug ativo. Ver seção 7 do memory.md para correções anteriores.

## 13. Como Submeter uma Tarefa a um Agente LLM

Para um novo agente continuar o desenvolvimento, fornecer:
1. O objetivo específico (ex: "implementar RAG pipeline")
2. O arquivo `explicando-licitai.md` como contexto
3. O arquivo `memory.md` para histórico de decisões
4. Os arquivos específicos que serão modificados
5. O comando de teste para validar (ex: `pytest e2e/tests/`)

### Comandos úteis:
```bash
# Rodar backend (dev nativo)
uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000

# Rodar frontend
cd frontend && npm run dev

# Rodar testes E2E (requer backend rodando)
$env:LLM_PROVIDER="gemini"; $env:RATE_LIMIT_MAX="6000"
pytest e2e/tests -v --tb=short

# Verificar sintaxe Python
python -c "import ast; ast.parse(open('arquivo.py', encoding='utf-8').read())"
```

## 14. Stack Tecnológica Detalhada

### Backend (Python 3.12):
- `fastapi==0.115.12`: Framework web async
- `uvicorn[standard]==0.34.3`: Servidor ASGI
- `sqlalchemy[asyncio]==2.0.41`: ORM com suporte async
- `asyncpg==0.30.0`: Driver PostgreSQL async
- `aiosqlite`: Driver SQLite async (fallback Windows)
- `pydantic-settings==2.9.1`: Validação de env vars
- `python-magic==0.4.27`: Detecção de MIME por magic bytes
- `pymupdf==1.25.5`: PDF parsing
- `pdfplumber==0.11.6`: PDF parsing (tabelas)
- `python-docx==1.1.2`: DOCX parsing
- `pytesseract==0.3.13`: OCR fallback
- `groq==0.25.0`: Cliente Groq API
- `google-genai==1.16.1`: Cliente Gemini API
- `httpx==0.28.1`: HTTP client
- `aiofiles==24.1.0`: File operations async
- `weasyprint==65.0`: Geração PDF (relatório)
- `markdown==3.8`: Markdown para HTML
- `greenlet==3.2.3`: Necessário no Windows para SQLAlchemy async

### Frontend (Node.js):
- Next.js 14 (App Router)
- React 18
- Tailwind CSS v3
- TypeScript

### Infraestrutura:
- Docker Compose (3 serviços)
- PostgreSQL 16 + pgvector
- Tesseract OCR (idioma português)
