# Sistema de Análise de Termos de Referência

Sistema especialista para análise automatizada de Termos de Referência (TR) de licitações públicas usando Inteligência Artificial.

## ✨ Funcionalidades (MVP)

- **Upload** de documentos PDF, DOCX e ODT
- **Parsing automático** com detecção de itens numerados, tabelas e anexos
- **OCR** para PDFs escaneados (Tesseract)
- **Múltiplos Agentes Inteligentes Especializados (Multi-Agent System)**:
  - ⚖️ **Agente Jurídico**: Auditagem estrita sob a Lei 14.133/21, Lei 13.303/16, TCU, AGU e CGU
  - 🛠️ **Agente Técnico**: Especificações técnicas, quantitativos, amostragem e SLAs
  - ✍️ **Agente de Redação**: Clareza textual, remoção de ambiguidade e ampla competitividade
  - 📐 **Agente Estrutural**: Organização e checklist dos 10 elementos do Art. 6º, XXIII
  - 👑 **Orquestrador Multi-Agente**: Execução concorrente assíncrona (`asyncio.gather`) + deduplicação de achados
- **RAG v1.0 & Corpus Jurídico Expandido**:
  - Embeddings semânticos com `get_embeddings_provider()` (Gemini / Ollama `bge-m3`)
  - **Jurisprudência do TCU** (Súmula 247, Súmula 272, Acórdão 1214/2013) e **RILC CODEBA-2023** (315 chunks no índice FTS5/Semântico)
  - **Comparador Visual de Versões de TR** (`/comparacao/versoes`): Alinhamento por item com identificação de `alterado`, `adicionado` e `removido`
- **Correções no formato DE → PARA** com fundamentação legal
- **Fluxo SEI Otimizado (Cópia em 1-clique)**:
  - 📋 **Copiar Texto Corrigido (PARA)**: Copia o trecho pronto para colar na cláusula do SEI
  - 📄 **Copiar Item Inteiro**: Copia a cláusula inteira com as correções aplicadas
  - 📝 **Copiar Parecer & Justificativa**: Copia o fundamento legal para o despacho/parecer do SEI
- **Relatório** com pontuação (0-10), nível de risco e parecer final
- **3 provedores de IA**: Groq (free tier), Google Gemini (free tier), Ollama (local) — com failover automático
- **Auditoria TR × Propostas** (módulo aditivo de conformidade):
  - **Moldes de regras configuráveis** (RF02): 10 tipos de âncoras (numéricas, por extenso, booleanas, legais, data, percentual, monetária, **CNPJ**, **prazo relativo** e **CEP**) com extração determinística + fallback LLM
  - **Editor visual de moldes** no frontend (`/moldes`): cria/edita regras, com **Duplicação de Molde em 1-clique** e **Validação Dry-Run em tempo real**
  - **Moldes padrão de seed**: TR geral, serviços continuados e obras públicas (`scripts/seed_moldes.py`)
  - **Matriz de conformidade** (RF03): compara TR vs propostas dos fornecedores com status **OK / ATENÇÃO / FALHA**
  - **Notificação de Pendências por E-mail (RF04)**: Envio automático via SMTP para fornecedores com pendências na matriz

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

## 🧹 Gerenciamento de Processos do Backend

Se o backend for iniciado várias vezes (ex.: no terminal e em background), podem restar **processos uvicorn duplicados** disputando a mesma porta. Os sintomas são: porta ocupada, respostas de uma versão antiga do código, ou `ChildProcess.kill` ao iniciar.

### 1. Listar todos os processos uvicorn

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "uvicorn" }
```

Identifique na saída: `ProcessId`, a porta (`--port 8000`, `--port 8001`) e qual interpretador está em uso (`backend\.venv\Scripts\python.exe` vs `Python\Python312\python.exe`).

### 2. Encerrar processos duplicados

Para encerrar **todos** os uvicorn de uma vez:

```powershell
Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match "uvicorn" -and $_.CommandLine -notmatch "Get-CimInstance" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Para encerrar apenas os processos de uma porta específica (ex.: 8001):

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq 8001 } |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

> **Dica**: os processos `uvicorn` com `--reload` deixam um processo pai (supervisor) e um filho (worker). Ambos são capturados pelo filtro acima.

### 3. Confirmar que as portas foram liberadas

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8000, 8001 }
```

Sem saída = portas livres. Em seguida, reinicie o backend normalmente (seção [Início Rápido](#-início-rápido)).

### 4. Limpar tudo (banco, uploads e logs)

Para remover o banco de desenvolvimento, arquivos de upload e logs de execução, deixando o projeto como recém-clonado (exceto `.env`):

```powershell
# Banco de dados (recriado automaticamente na próxima inicialização)
Remove-Item licitacao.db -Force -ErrorAction SilentlyContinue
Remove-Item e2e-test.db -Force -ErrorAction SilentlyContinue

# Arquivos de upload
Remove-Item backend/uploads\* -Force -Recurse -ErrorAction SilentlyContinue
Remove-Item e2e-uploads -Recurse -Force -ErrorAction SilentlyContinue

# Logs de execução do backend
Remove-Item backend\server_stdout.log, backend\server_stderr.log -Force -ErrorAction SilentlyContinue
Remove-Item backend\test_stdout.log, backend\test_stderr.log -Force -ErrorAction SilentlyContinue

# Diretório de trabalho do SQLite (WAL)
Remove-Item licitacao.db-wal, licitacao.db-shm -Force -ErrorAction SilentlyContinue
Remove-Item e2e-test.db-wal, e2e-test.db-shm -Force -ErrorAction SilentlyContinue
```

> ⚠️ **Atenção**: os comandos acima apagam dados locais de desenvolvimento. Não os execute se quiser preservar documentos enviados ou análises já realizadas.

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
│       │   ├── llm/         # Groq, Gemini, Ollama providers
│       │   ├── analyzer/    # Motor de análise + prompts
│       │   ├── rules/       # Moldes de regras (loader, extractor, fallback LLM)
│       │   └── comparator/  # Comparação TR × Propostas (comparator, matrix)
│       └── utils/           # Segurança, validação de uploads
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/             # Pages (Dashboard, Upload, Análise, Relatório, Comparações)
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
# 1. Iniciar backend (provedores reais: Gemini/Groq via failover)
$env:LLM_PROVIDER="gemini"; $env:RATE_LIMIT_MAX="6000"
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# 2. Rodar testes (em outro terminal)
$env:E2E_BASE_URL="http://127.0.0.1:8000"; $env:PYTHONPATH="backend"
backend\.venv\Scripts\python.exe -m pytest e2e/tests -v --tb=short
```

- **17 testes** cobrindo health check, upload, CRUD, análise e relatório
- Fluxo completo: upload → parsing → análise → relatório
- Testes de borda: extensão inválida, documento não encontrado
- Os testes usam provedores de IA reais (sem mock); exigem chaves de API válidas

### Testes unitários do módulo de auditoria (RF02/RF03)

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_rules_loader.py tests\test_extractor.py tests\test_comparator.py tests\test_matrix.py -v
```

- **40 testes** cobrindo validação de moldes, extração por âncoras (numérica/extensa/booleana/legal/data/percentual/monetária), classificação OK/FALHA/ATENÇÃO e montagem da matriz.

## 🧪 API do Módulo de Auditoria (RF02/RF03)

Todas as rotas sob `/api/v1`:

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/fornecedores` | Cadastra fornecedor |
| GET / PUT / DELETE | `/fornecedores/{id}` | CRUD de fornecedor |
| POST | `/moldes` | Cria molde de regras (valida config_json) |
| GET / PUT / DELETE | `/moldes/{id}` | CRUD de molde |
| POST | `/documents/upload` | Upload com `document_type=tr\|proposta` + `fornecedor_id` |
| POST | `/comparison/start` | Inicia comparação TR × propostas (202, background) |
| GET | `/comparison` | Lista comparações |
| GET | `/comparison/{id}` | Status e totais |
| GET | `/comparison/{id}/matrix` | Matriz de conformidade regras × fornecedores |

### Formato do `config_json` de um molde

```json
{
  "versao": 1,
  "regras": [
    { "id": "vigencia_dias", "rotulo": "Vigência mínima", "tipo": "numero_inteiro",
      "ancora": "vigência", "expectativa": 90 },
    { "id": "garantia", "rotulo": "Garantia", "tipo": "booleano",
      "palavras_chave": ["garantia", "caução"] },
    { "id": "lei_14133", "rotulo": "Lei 14.133/2021", "tipo": "legal",
      "regex": "14\\.133/2021" }
  ]
}
```

Tipos suportados: `numero_inteiro`, `numero_extenso`, `booleano`, `legal`, `data`, `percentual`, `monetario`.

### Seed de moldes padrão

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\seed_moldes.py
```

Cria (idempotente) os moldes: **Molde Padrão de TR**, **Molde de Serviços Continuados** e **Molde de Obras Públicas**.

> **Delete protegido**: moldes com comparações vinculadas e fornecedores com propostas retornam `409` ao tentar exclusão (integridade referencial).

## 📋 Roadmap

- [x] **MVP**: Upload, parsing, análise com IA, relatório
- [x] **RF02/RF03**: Auditoria TR × Propostas — moldes de regras + matriz de conformidade
- [x] **Auditoria (polimentos)**: editor visual de moldes + seed + tipos data/percentual/monetário
- [ ] **v1.0**: RAG com legislação, busca semântica, histórico
- [x] **RF04**: Feedback/e-mail por fornecedor (endpoint + UI; requer `SMTP_HOST`/`SMTP_FROM` no `.env`)
- [ ] **v2.0**: Múltiplos agentes, checklist de conformidade, multi-usuário

## 📄 Licença

Uso interno — Codeba.
