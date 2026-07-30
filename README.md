# Sistema de Análise de Termos de Referência

Sistema especialista para análise automatizada de Termos de Referência (TR) de licitações públicas usando Inteligência Artificial.

## ✨ Funcionalidades (MVP)

- **Upload** de documentos PDF e DOCX
- **Parsing automático** com detecção de itens numerados, tabelas e anexos
- **OCR** para PDFs escaneados (Tesseract)
- **Análise por IA** item a item em 4 dimensões:
  - 🟣 Jurídica (conformidade legal, riscos de impugnação)
  - 🔵 Técnica (especificações, quantitativos, prazos)
  - 🟡 Redação (clareza, ambiguidades, objetividade)
  - 🟢 Estrutural (numeração, referências, organização)
- **Correções no formato DE → PARA** com fundamentação legal
- **Fluxo SEI Otimizado (Cópia em 1-clique)**:
  - 📋 **Copiar Texto Corrigido (PARA)**: Copia o trecho pronto para colar na cláusula do SEI
  - 📄 **Copiar Item Inteiro**: Copia a cláusula inteira com as correções aplicadas
  - 📝 **Copiar Parecer & Justificativa**: Copia o fundamento legal para o despacho/parecer do SEI
- **Relatório** com pontuação (0-10), nível de risco e parecer final
- **4 provedores de IA**: Groq (free tier), Google Gemini (free tier), Ollama (local), Mock (testes)

## 🛠 Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Frontend | Next.js 14, React, Tailwind CSS 3, TypeScript |
| Backend | FastAPI, Python 3.12, SQLAlchemy (async) |
| Banco | PostgreSQL 16 (pgvector) ou SQLite (aiosqlite nativo) |
| Parser | PyMuPDF, pdfplumber, python-docx, Tesseract OCR, python-magic-bin |
| IA | Groq API, Google Gemini API, Ollama |
| Deploy | Docker Compose ou Execução Nativa Windows (sem Docker) |

## 🚀 Início Rápido

### Modo Nativo Windows (Sem necessidade de Docker ou BIOS)

```powershell
# 1. Backend (FastAPI) — utiliza venv e SQLite automático
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000

# 2. Frontend (Next.js) — em outro terminal
cd frontend
npm run dev

# 3. Acessar no navegador:
# Frontend: http://localhost:3000
# API docs: http://127.0.0.1:8000/api/docs
```

### Com Docker (Containers)

```bash
# 1. Configurar variáveis de ambiente (.env)
cp .env.example .env

# 2. Subir todos os serviços
docker compose up --build
```

### Chaves de API (gratuitas)

| Provedor | Onde obter | Free Tier |
|----------|-----------|-----------|
| **Groq** | [console.groq.com](https://console.groq.com) | ~30 req/min, Llama 3.3 70B |
| **Google Gemini** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | 1500 req/dia, Gemini 2.0 Flash |
| **Ollama** | [ollama.com](https://ollama.com) | Ilimitado (local) |

## 📁 Estrutura do Projeto

```
licitacao/
├── docker-compose.yml       # Orquestração
├── .env.example             # Template de configuração
├── db/init.sql              # Schema do banco
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI + middlewares
│       ├── config.py        # Settings (env vars)
│       ├── database.py      # SQLAlchemy async
│       ├── models/          # ORM models
│       ├── schemas/         # Pydantic validation
│       ├── api/             # REST endpoints
│       ├── services/
│       │   ├── parser/      # PDF, DOCX, OCR, estruturador
│       │   ├── llm/         # Groq, Gemini, Ollama, Mock providers
│       │   └── analyzer/    # Motor de análise + prompts
│       └── utils/           # Segurança, validação de uploads
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/             # Pages (Dashboard, Upload, Análise, Relatório)
│       ├── components/      # Layout (Sidebar, Header)
│       ├── lib/api.ts       # Cliente API
│       └── types/           # TypeScript types
└── e2e/                     # Testes End-to-End
    ├── .env.test            # Config para testes
    ├── run_e2e.ps1          # Script automatizado
    ├── fixtures/            # Documentos de exemplo
    ├── scripts/             # Scripts auxiliares
    └── tests/               # Testes pytest + httpx
```

## 🔒 Segurança

- Validação de uploads (allowlist de extensões + magic bytes)
- Renomeação de arquivos para UUID (nunca usa nome original)
- Prevenção de path traversal
- CSP strict + X-Frame-Options DENY
- Rate limiting configurável via env `RATE_LIMIT_MAX` (padrão 600 req/min)
- CORS com allowlist de origens
- SQL via ORM (sem string concatenation)
- Secrets via variáveis de ambiente (nunca hardcoded)
- XXE prevention no parsing de DOCX
- Portas bind em 127.0.0.1

## 🧪 Testes E2E

```powershell
# 1. Iniciar backend com mock provider
$env:LLM_PROVIDER="mock"; $env:RATE_LIMIT_MAX="6000"
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# 2. Rodar testes (em outro terminal)
$env:E2E_BASE_URL="http://127.0.0.1:8000"; $env:PYTHONPATH="backend"
backend\.venv\Scripts\python.exe -m pytest e2e/tests -v --tb=short
```

- **17 testes** cobrindo health check, upload, CRUD, análise e relatório
- Fluxo completo: upload → parsing → análise → relatório
- Testes de borda: extensão inválida, documento não encontrado

## 📋 Roadmap

- [x] **MVP**: Upload, parsing, análise com IA, relatório
- [ ] **v1.0**: RAG com legislação, busca semântica, histórico
- [ ] **v2.0**: Múltiplos agentes, checklist de conformidade, multi-usuário

## 📄 Licença

Uso interno — Codeba.
