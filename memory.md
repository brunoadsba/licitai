# Contexto e Memória do Projeto: Sistema Especialista em Análise de TR (SEI)

Este arquivo serve como **fonte da verdade e memória contínua** para qualquer agente de IA ou desenvolvedor dar prosseguimento ao projeto sem perda de contexto.

---

## 1. Visão Geral do Projeto

O **Sistema Especialista em Análise de Termos de Referência (SEI)** é uma aplicação full-stack desenhada para analisar, revisar e aperfeiçoar Termos de Referência (TR) elaborados para licitações públicas (com foco nas Leis 14.133/2021 e 13.303/2016, RILC, TCU, AGU e CGU).

### Principais Objetivos do MVP:
- Upload de documentos em **PDF** e **DOCX**.
- **Parsing e estruturação hierárquica automática** (seções, itens 1.1, subitens 1.1.1, alíneas, cláusulas e anexos).
- **OCR automático com Tesseract** como fallback para PDFs escaneados (sem texto selecionável).
- **Análise item a item via IA** em 4 dimensões (Jurídica, Técnica, Redação e Estrutural).
- Sugestões de melhoria fundamentadas no formato **DE → PARA** (com gravidade, risco, justificativa e embasamento legal).
- **Fluxo de Trabalho Otimizado para o SEI (Sem necessidade de downloads)**:
  - O usuário trabalha editando diretamente o formulário/cláusula no sistema SEI.
  - A interface disponibiliza **botões de cópia em 1-clique** (`Copiar Texto Corrigido (PARA)`, `Copiar Item Inteiro com Correções`, `Copiar Parecer Final` e `Copiar Justificativa/Fundamento Legal`) com feedback visual ("Copiado!").
- **Pontuação consolidada (0-10)** por dimensão, nível de risco do documento e emissão de parecer técnico final.

---

## 2. Arquitetura e Decisões de Design

- **Frontend**: Next.js 14 (App Router), React 18, Tailwind CSS v3 (Tema escuro premium com Glassmorphism, badges de risco/categoria e animações), TypeScript.
  - **Proxy Rewrites (`next.config.js`)**: Redirecionamento dinâmico de `/api/*` via `BACKEND_URL` (padrão `http://127.0.0.1:8000` no modo nativo e `http://backend:8000` no Docker).
- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.0 (Async com `asyncpg` e `aiosqlite`), Pydantic v2.
- **Banco de Dados (Duplo Suporte)**:
  - **Produção/Docker**: PostgreSQL 16 com extensão `pgvector` e `uuid-ossp` (preparado para RAG na v1.0).
  - **Modo Nativo (Windows sem Docker)**: SQLite Async com `aiosqlite` (`licitacao.db` criado automaticamente sem dependência da BIOS/Docker).
- **Provedores de LLM (Factory Pattern)**:
  - **Groq API** (`groq_provider.py`) — *Default MVP Free Tier*: `llama-3.3-70b-versatile`.
  - **Google Gemini API** (`gemini_provider.py`) — *Secundário Free Tier*: `gemini-2.0-flash`.
  - **Ollama** (`ollama_provider.py`) — *Local*: `qwen3:32b`, `deepseek-r1:32b`, etc.
- **Compatibilidade Windows**:
  - `python-magic-bin` instalado para validação de magic bytes sem dependências C externas no Windows.
  - `UPLOAD_DIR` configurado dinamicamente para `./uploads`.
- **Segurança**:
  - Content Security Policy (CSP) restritivo, headers de segurança (X-Frame-Options DENY, X-Content-Type-Options nosniff).
  - Rate limiting in-memory (60 req/min).
  - Validação rigorosa de uploads (allowlist de extensão + validação por magic bytes).
  - Nomes de arquivos armazenados renomeados para UUIDs (fora do web root).

---

## 3. Mapeamento de Arquivos da Aplicação

### Raiz
- `docker-compose.yml`: Orquestração de 3 containers (`db`, `backend`, `frontend`).
- `.env`: Configurações de ambiente (`DATABASE_URL`, `LLM_PROVIDER`, `GROQ_API_KEY`, `POSTGRES_PASSWORD`).
- `.env.example`: Template de configuração.
- `README.md`: Guia completo de instalação, segurança e arquitetura.
- `memory.md`: Memória contínua do projeto.
- `db/init.sql`: Script de criação das extensões, tabelas (`documents`, `document_items`, `analyses`, `corrections`), índices e triggers no PostgreSQL.

### Backend (`/backend`)
- `Dockerfile`: Imagem Python 3.12-slim com `tesseract-ocr`, `tesseract-ocr-por` e `libmagic1`.
- `requirements.txt`: Dependências do Python (FastAPI, SQLAlchemy, PyMuPDF, pdfplumber, python-docx, groq, google-genai, aiosqlite, python-magic-bin, etc.).
- `app/main.py`: Aplicação FastAPI, middlewares de segurança (CSP, CORS allowlist, Rate Limit) e health check.
- `app/config.py`: Validação de variáveis de ambiente com Pydantic Settings (`extra="ignore"` habilitado).
- `app/database.py`: Conexão assíncrona SQLAlchemy (suporta `postgresql+asyncpg` e `sqlite+aiosqlite`).
- `app/models/`:
  - `document.py`: Modelos ORM `Document` e `DocumentItem`.
  - `analysis.py`: Modelos ORM `Analysis` e `Correction`.
- `app/schemas/`:
  - `document.py`: Schemas Pydantic de requisição e resposta de documentos.
  - `analysis.py`: Schemas Pydantic de análises, correções e relatórios.
- `app/api/`:
  - `router.py`: Router `/api/v1`.
  - `documents.py`: Endpoints `/documents/upload`, `/documents/`, `/documents/{id}` e DELETE.
  - `analysis.py`: Endpoints `/analysis/{document_id}/start` (Background Task), `/analysis/{analysis_id}`, `/analysis/{analysis_id}/report`.
- `app/services/parser/`:
  - `pdf_parser.py`: PyMuPDF primário -> pdfplumber fallback (tabelas) -> Tesseract OCR.
  - `docx_parser.py`: Extração via `python-docx` com detecção de estilos e tabelas.
  - `structurer.py`: Regex para extração da árvore de itens numerados e anexos.
- `app/services/llm/`:
  - `provider.py`: Classe abstrata `LLMProvider` e factory `get_llm_provider()`.
  - `groq_provider.py`, `gemini_provider.py`, `ollama_provider.py`: Implementações dos provedores.
- `app/services/analyzer/`:
  - `prompts.py`: Persona do Especialista Sênior, regras estritas de não alteração cosmética e prompts JSON.
  - `engine.py`: Motor de execução da análise item a item + pontuação global + reparo de JSON.
  - `report.py`: Gerador de relatórios em Markdown formatado.
- `app/utils/`:
  - `file_validation.py`: Validação de extensão, magic bytes, tamanho e caminho seguro (`UPLOAD_DIR`).
  - `security.py`: Middlewares `SecurityHeadersMiddleware` e `RateLimitMiddleware`.

### Frontend (`/frontend`)
- `next.config.js`: Proxy rewrites dinâmicos apontando para `BACKEND_URL` (`http://127.0.0.1:8000`).
- `package.json`: Next.js 14, React 18, Tailwind CSS v3.
- `src/types/index.ts`: Mapeamento TypeScript dos schemas da API e rótulos amigáveis em PT-BR.
- `src/lib/api.ts`: Cliente HTTP para chamadas assíncronas ao backend.
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

- **Backend FastAPI Rodando Ativamente**: O servidor FastAPI está em execução em **http://127.0.0.1:8000** (Health Check `/health` respondendo `{"status": "ok", "provider": "groq"}`).
- **Frontend Next.js Rodando Ativamente**: O servidor Next.js está em execução em **http://localhost:3000** (proxy API redirecionando perfeitamente para `http://127.0.0.1:8000/api/*`).
- **Banco de Dados Nativo**: O banco SQLite (`licitacao.db`) está inicializado com todas as tabelas criadas (`documents`, `document_items`, `analyses`, `corrections`).
- **Chave de API**: Variável `GROQ_API_KEY` configurada no `.env` e validada pelo provedor Groq.
- Todos os **31 arquivos Python** e **9 arquivos TypeScript** foram verificados e compilados sem erros.

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

### Modo Docker (Containers para Produção):
```bash
docker compose up --build
```

---

## 7. Próximos Passos (Roadmap para Próximos Agentes)

- **v1.0**:
  - Implementar pipeline RAG (Retrieval-Augmented Generation) armazenando trechos da Lei 14.133, Lei 13.303, RILC e acórdãos do TCU na tabela `pgvector`.
  - Integrar embeddings (ex: OpenAI `text-embedding-3-small` ou `BAAI/bge-m3`).
  - Adicionar funcionalidade de comparação entre diferentes versões do mesmo TR.
- **v2.0**:
  - Múltiplos agentes especializados utilizando LangGraph (Agente Jurídico, Agente Técnico, Agente de Redação, Agente Revisor).
  - Autenticação e controle de acesso (RBAC).
