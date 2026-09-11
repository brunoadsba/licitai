# Sistema de Análise de Termos de Referência

Sistema especialista para análise automatizada de Termos de Referência (TR) de licitações públicas usando Inteligência Artificial.

## Job único (piloto)

Produto focado no **elaborador de TR**: enviar documento → revisar achados prioritários (IA sugere; você decide) → copiar só o aprovado/ajustado para o SEI. Módulos de auditoria TR×propostas ficam em “Mais ferramentas”.

**Guia do usuário (elaboradores):** [docs/guia-usuario.md](docs/guia-usuario.md)

Ops e pendências do piloto (gate 14 dias, cron, DOCX, Art. 6, fixtures): ver [docs/ops/piloto.md](docs/ops/piloto.md).

### Entregas recentes (piloto)

- Pacote SEI, TR HTML/DOCX corrigido, fila Prioridade, checklist Art. 6º com **`art6_coverage` ≥90%**
- Modo `economic`, reanálise parcial, painel de pendências
- Base local de TRs: [`fixtures/trs-codeba/`](fixtures/trs-codeba/) (12 objetos; PDFs fora do Git)
- UI: tema **claro/escuro** (toggle no header) — contrato em [`frontend/DESIGN.md`](frontend/DESIGN.md)
- UX elaborador (11/09): Enviar → Revisar agora → pacote SEI; relatório = leitura/PDF; copiloto sob demanda; guia em `/guia`

## Funcionalidades (MVP)

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
  - **Busca sem acento** (FTS5 `remove_diacritics 2`): consultas com/sem acentuação retornam os mesmos resultados
  - **Retrieval híbrido RRF**: combina busca semântica + textual com fusão por rank recíproco
  - **Comparador Visual de Versões de TR** (`/comparacao/versoes`): Alinhamento por item com identificação de `alterado`, `adicionado` e `removido`
- **Correções no formato DE → PARA** com fundamentação legal
- **Fluxo SEI (cópia filtrada + revisão humana)**:
  - Revisão cruzada LLM + **revisão humana** (Aprovar / Rejeitar / Ajustar) via `PATCH /api/v1/analysis/corrections/{id}`
  - Cópia para o SEI **somente** com correções `aprovada` ou `ajustada`
  - **Fila Prioridade** (alto/crítico + Art. 6º/estrutural) na análise
  - **Copiar pacote SEI** (`GET /analysis/{id}/sei-pack`), **TR HTML** (`…/corrected-html`) e **DOCX** (`…/corrected-docx`)
  - **Checklist Art. 6º XXIII** com cobertura estrutural (`art6_coverage` / meta ≥90%)
- **Relatório** com pontuação (0-10), nível de risco, parecer final e **Exportar PDF** (impressão do navegador)
- **Upload honesto**: após o parse, a análise LLM inicia automaticamente (“Enviar e Analisar”)
- **3 provedores de IA**: Groq (free tier), Google Gemini (free tier), Ollama (local) — com failover automático
- **Auditoria TR × Propostas** (módulo aditivo de conformidade):
  - UI em abas: Histórico / Nova auditoria / Fornecedores
  - **Moldes de regras configuráveis** (RF02): 10 tipos de âncoras (numéricas, por extenso, booleanas, legais, data, percentual, monetária, **CNPJ**, **prazo relativo** e **CEP**) com extração determinística + fallback LLM
  - **Editor visual de moldes** no frontend (`/moldes`): cria/edita regras, com **Duplicação de Molde em 1-clique** e **Validação Dry-Run em tempo real**
  - **Moldes padrão de seed**: TR geral, serviços continuados e obras públicas (`scripts/seed_moldes.py`)
  - **Matriz de conformidade** (RF03): compara TR vs propostas dos fornecedores com status **OK / ATENÇÃO / FALHA**
  - **Notificação de Pendências por E-mail (RF04)**: Envio automático via SMTP para fornecedores com pendências na matriz
- **Copiloto LicitAI (chat consultivo)**:
  - Desktop: painel docked; **mobile: FAB + sheet** full-height com focus trap
  - **Respostas sempre ancoradas em fontes citadas** (RAG jurídico, análise, correções, itens do documento) ou recusa explícita
  - Badges de ancoragem/confiança, provedor e latência; acordeão de fontes; feedback 👍/👎
  - API `/api/v1/chat` (health, conversas, mensagens, feedback) com validação de tamanho e guards 404/400/422
  - Modo demo/teste com provider fake (`CHAT_FORCE_FAKE_PROVIDER=True`) — sem chamadas de IA real

## 🛠 Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Frontend | Next.js 14, React, Tailwind CSS 3, TypeScript, tema claro/escuro |
| Backend | FastAPI, Python 3.12, SQLAlchemy (async) |
| Banco | PostgreSQL 16 (pgvector) ou SQLite (aiosqlite nativo) |
| Parser | PyMuPDF, pdfplumber, python-docx, Tesseract OCR, python-magic-bin |
| IA | Groq API, Google Gemini API, Ollama |
| Validação de schema | pglast (parser oficial do PostgreSQL) |
| Deploy | Docker Compose ou Execução Nativa Windows (sem Docker) |

## 🚀 Como Executar o Projeto (Passo a Passo)

### Docker Compose (piloto WSL — recomendado)

```bash
./scripts/up.sh            # unset env sujo + compose up -d + smoke
./scripts/up.sh --build    # após mudança de frontend/imagem
./scripts/down.sh          # para containers; não apaga pgdata
```

UI: `http://127.0.0.1:3000/` · API: `http://127.0.0.1:8000/` · Ops: [docs/ops/piloto.md](docs/ops/piloto.md), [docs/ops/deploy.md](docs/ops/deploy.md).

### 1️⃣ Terminal 1: Iniciar o Backend (FastAPI + Python)

O backend executa na porta `8000` usando o ambiente virtual Python `.venv`.

```powershell
# 1. No terminal, navegue para a raiz do projeto:
cd c:\Users\bruno.santos\Downloads\Bruno\Codeba\projetos-tech\licitacao

# 2. Inicie o servidor FastAPI via Uvicorn:
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```
> 📍 **URL do Backend**: `http://127.0.0.1:8000`  
> 📑 **Documentação da API (Swagger)**: `http://127.0.0.1:8000/docs`

Análises e comparações vão para a fila `jobs` e **só avançam com o worker**:

```powershell
# Terminal extra (ou serviço Compose `worker`):
cd backend
..\.venv\Scripts\python.exe -m app.worker
# Linux/WSL: PYTHONPATH=. .venv/bin/python -m app.worker
```

---

### 2️⃣ Terminal 2: Iniciar o Frontend (Next.js + React)

O frontend executa na porta `3000` usando Node.js.

```powershell
# 1. Abra um NOVO terminal e entre na pasta do frontend:
cd c:\Users\bruno.santos\Downloads\Bruno\Codeba\projetos-tech\licitacao\frontend

# 2. Inicie o servidor de desenvolvimento do Next.js:
npm run dev
```
> 🌐 **URL da Aplicação Web**: `http://localhost:3000`

---

### 3️⃣ Extensão de Navegador para o SEI (Opcional)

Para conectar o LicitAI diretamente ao editor de textos do **SEI**:

1. Acesse no Chrome/Edge: `chrome://extensions` ou `edge://extensions`.
2. Ative o **Modo do Desenvolvedor** no canto superior direito.
3. Clique em **"Carregar sem compactação"** (Load unpacked).
4. Selecione a pasta `extension/` do projeto (`licitacao/extension`).
5. O ícone do **LicitAI** 🪄 aparecerá na barra do navegador para injeção automática de TRs.

---

### 🔑 Configuração de Chaves de IA (`.env`)

| Provedor | Onde obter | Free Tier |
|----------|-----------|-----------|
| **Groq** | [console.groq.com](https://console.groq.com) | ~30 req/min, Llama 3.3 70B |
| **Google Gemini** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Cota diária limitada (429 possível sob uso intenso), Gemini 2.0 Flash |
| **Ollama** | [ollama.com](https://ollama.com) | Ilimitado (local) — `qwen3:32b` (padrão) ou `hermes3` (mais leve, bom em JSON/instruções; ideal p/ TRs sigilosos) |

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
├── docker-compose.yml       # db + backend + worker + frontend
├── .env.example             # Template (API_TOKEN server-side; sem NEXT_PUBLIC_*)
├── db/init.sql              # Schema PostgreSQL (alinhado ao Alembic)
├── memory.md                # Memória contínua (contexto p/ agentes)
├── docs/ops/                # Deploy, restore, SLOs, piloto, gate 14d, cron
├── fixtures/trs-codeba/     # TRs CODEBA locais (PDFs gitignored)
├── scripts/                 # up/down Compose, backup, cron, smoke_readyz, score_art6_fixtures
├── backend/
│   ├── Dockerfile
│   ├── alembic/             # Migrações (head 20260908_003)
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI + /livez /readyz /metrics
│       ├── worker.py        # Processa fila jobs (obrigatório)
│       ├── config.py        # Settings (env vars)
│       ├── database.py      # SQLAlchemy async
│       ├── models/          # ORM models
│       ├── schemas/         # Pydantic validation
│       ├── api/             # REST (start = enqueue-only)
│       ├── services/
│       │   ├── parser/      # PDF, DOCX, OCR, estruturador
│       │   ├── llm/         # Groq, Gemini, Ollama + limiter
│       │   ├── analyzer/    # Motor + review fail-closed
│       │   ├── jobs/        # Fila durável
│       │   ├── legal/       # Checklist Art. 6 XXIII a–j
│       │   ├── rules/       # Moldes de regras
│       │   └── comparator/  # TR × Propostas
│       └── utils/           # Segurança, validação de uploads
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/             # Pages + api/proxy (BFF)
│       ├── components/      # Layout + UI
│       ├── lib/api.ts       # Cliente via BFF
│       └── types/           # TypeScript types
└── e2e/                     # E2E + golden/ (FakeLLM)
    ├── .env.test            # Config para testes
    ├── run_e2e.ps1          # Script automatizado
    ├── fixtures/            # Documentos de exemplo
    ├── scripts/             # Scripts auxiliares
    └── tests/               # Testes pytest + httpx
```

## 🔒 Segurança

- Validação de uploads (allowlist de extensões + magic bytes + checagem de tamanho pré-leitura)
- Renomeação de arquivos para UUID (nunca usa nome original)
- Prevenção de path traversal
- CSP strict + X-Frame-Options DENY (API **e** páginas do frontend)
- Token opcional de API: defina `API_TOKEN` (backend e BFF Next.js server-side) para exigir o header `X-API-Token` em `/api/v1`; o browser nunca recebe o token. Vazio = sem autenticação (piloto local)
- Rate limiting configurável via env `RATE_LIMIT_MAX` (padrão 600 req/min)
- CORS com allowlist de origens
- SQL via ORM (sem string concatenation)
- Secrets via variáveis de ambiente (nunca hardcoded)
- XXE prevention no parsing de DOCX
- Portas bind em 127.0.0.1
- `PRAGMA foreign_keys=ON` no SQLite: os `ondelete CASCADE/SET NULL` dos models valem também no SQLite, alinhado ao PostgreSQL

## 💾 Backup do banco (SQLite)

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/backup_db.py                 # ./licitacao.db -> ./backups/
PYTHONPATH=. .venv/bin/python scripts/backup_db.py --origem ../licitacao.db --destino /caminho/backups
```

Usa a API de backup nativa do SQLite (segura com WAL ativo). Agende via cron/Agendador de Tarefas para execução diária. Para PostgreSQL use `pg_dump`.

## 🧬 Migrações manuais de schema

O `Base.metadata.create_all` do startup não altera tabelas existentes. Após atualizar o código, rode os scripts idempotentes conforme a versão de origem:

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/migrate_unique_constraints.py   # índices únicos de revisões e análises ativas
```

(Outros: `scripts/migrate_agent_columns.py`, `scripts/migrate_review_columns.py`.)

## 🧪 Testes E2E

```powershell
# 1. Iniciar backend (provedores reais: Gemini/Groq via failover)
# IMPORTANTE: o config.py lê o .env relativo ao CWD — carregue as variáveis da raiz no processo:
$env:LLM_PROVIDER="gemini"; $env:GEMINI_API_KEY="<chave>"; $env:RATE_LIMIT_MAX="6000"
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# 2. Rodar testes (em outro terminal)
$env:E2E_BASE_URL="http://127.0.0.1:8000"; $env:PYTHONPATH="backend"
backend\.venv\Scripts\python.exe -m pytest e2e/tests -v --tb=short
```

- **17 testes** cobrindo health check, upload, CRUD, análise e relatório
- Fluxo completo: upload → parsing → análise → relatório
- Testes de borda: extensão inválida, documento não encontrado
- Os testes usam provedores de IA reais (sem mock); exigem chaves de API válidas
- O fixture de análise aguarda até **240s** (o LLM real sob cota free tier pode passar de 60s; 4 testes podem estourar o timeout se a cota diária de Gemini/Groq estiver esgotada)

### Testes unitários

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
```

```bash
# Linux / WSL
cd /caminho/licitai
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q
```

- Cobertura: parser, extractor, retriever, rules/comparador/matriz, multi-agente, schema, chat/Copiloto, revisão humana SEI (`test_correction_review_api.py`), demais módulos.
- `backend/tests/conftest.py` força `DATABASE_URL=sqlite+aiosqlite:///:memory:` **antes** do import de `app.*`, para o pytest não herdar `postgresql://` síncrono do `.env`.
- Testes do Copiloto usam **provider fake** (determinístico) — nunca chamam Gemini/Groq/Ollama reais.
### Validação do schema PostgreSQL (`db/init.sql`)

Sem Docker, o `db/init.sql` é validado contra a **gramática oficial do PostgreSQL** via `pglast` (libpg_query) em `tests/test_init_sql.py` (16 testes):

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_init_sql.py -v
```

Verifica sintaxe válida + contrato de schema: `document_items` fechado, `items_snapshot JSON`, `analysis_mode`, `agent_origin`, `embedding TEXT`, constraint `uq_comparacao_fornecedor_regra`, tabelas do Copiloto (`chat_conversations`/`chat_messages` com `context_json`/`sources` JSON, check de `role`, constraint `uq_chat_messages_conversation_role`) e ausência de índice ivfflat sobre embedding. Para validação de runtime em Postgres real, use `docker compose up -d db` (o `init.sql` é aplicado automaticamente no 1º boot do volume `pgdata`).

### Testes unitários do módulo de auditoria (RF02/RF03)

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_rules_loader.py tests\test_extractor.py tests\test_comparator.py tests\test_matrix.py -v
```

- **40 testes** cobrindo validação de moldes, extração por âncoras (numérica/extensa/booleana/legal/data/percentual/monetária), classificação OK/FALHA/ATENÇÃO e montagem da matriz.

### Benchmark comparativo de modelos (`scripts/benchmark_modelos.py`)

Compara modelos lado a lado nos TRs fixture usando os **mesmos prompts de produção**, medindo por modelo: aderência ao formato DE→PARA (JSON válido), recall (grounding nos problemas esperados), % de correções com fundamento legal e latência média:

```powershell
cd backend
# Baixe os modelos locais antes (uma vez):
ollama pull hermes3
ollama pull qwen3:32b

# Roda todos (Groq llama-3.1-8b + Hermes 3 8B local + Qwen3 32B local):
.\.venv\Scripts\python.exe scripts\benchmark_modelos.py
# Só locais, apontando para o Ollama na sua máquina (execução nativa Windows):
.\.venv\Scripts\python.exe scripts\benchmark_modelos.py --models hermes3,qwen3 --ollama-base-url http://localhost:11434
```

- Requer `GROQ_API_KEY` no `.env` apenas para o modelo Groq; os modelos Ollama rodam 100% local (privacidade para TRs sigilosos).
- Saídas em `backend/`: `benchmark_modelos_report.json` (métricas detalhadas) e `benchmark_modelos_report.md` (tabela markdown comparativa).
- Para usar Hermes 3 no fluxo normal, defina `OLLAMA_MODEL=hermes3` no `.env` (veja [Configuração de Chaves de IA](#-configuração-de-chaves-de-ia-env)).

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

### Reingestão do corpus jurídico (RAG)

Reconstrói o índice FTS5 (com `remove_diacritics 2`) e regenera os embeddings semânticos. **Rode os scripts sequencialmente** — execução paralela contra o mesmo SQLite pode causar corrida no rebuild do FTS:

```powershell
# Carregue as chaves do .env da raiz no processo antes de rodar:
Get-Content .env | Where-Object { $_ -match '^[A-Z_]+=' } | ForEach-Object {
  $kv = $_ -split '=',2; [Environment]::SetEnvironmentVariable($kv[0], $kv[1])
}

cd backend
.\.venv\Scripts\python.exe scripts\ingest_laws.py
.\.venv\Scripts\python.exe scripts\ingest_juris_tcu.py
.\.venv\Scripts\python.exe scripts\ingest_corpus_extra.py
.\.venv\Scripts\python.exe scripts\ingest_embeddings.py
```

Resultado esperado: **7 documentos, 315 chunks, 100% com embedding**. Dica: se `ingest_embeddings.py` falhar com `429 RESOURCE_EXHAUSTED`, aguarde ~60s (cota free tier de ~100 req/min do Gemini) e rode novamente — o script é idempotente (só processa chunks sem embedding).

## 💬 API do Copiloto (Chat Consultivo)

Todas as rotas sob `/api/v1`:

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/chat/health` | Status/configuração do Copiloto |
| POST | `/chat/conversations` | Cria conversa (201), opcionalmente vinculada a documento/análise |
| GET | `/chat/conversations` | Lista conversas (paginado por `updated_at` desc) |
| GET | `/chat/conversations/{id}/messages` | Mensagens da conversa (404 se inexistente) |
| POST | `/chat/conversations/{id}/messages` | Envia mensagem e retorna resposta com fontes (422 se conteúdo vazio/estouro) |
| POST | `/chat/messages/{id}/feedback` | Feedback `up`/`down` (400 em mensagem do usuário, 404 inexistente, 422 rating inválido) |

Regras de comportamento:
- **Grounding obrigatório** (padrão): resposta factual exige pelo menos uma citação válida; sem fontes, o Copiloto recusa explicitamente.
- `suggested_actions` geradas pelo LLM são **descartadas** no MVP — o chat é somente-leitura em relação às entidades de negócio.
- **Modo fake** para demo/teste (sem IA real): `CHAT_FORCE_FAKE_PROVIDER=True`.
- Configurações: `CHAT_ENABLED`, `CHAT_REQUIRE_GROUNDING`, `CHAT_TOP_K_SOURCES`, `CHAT_MAX_MESSAGE_LENGTH`, `CHAT_MAX_SOURCES_STORED`.

## 📋 Roadmap

- [x] **MVP**: Upload, parsing, análise com IA, relatório
- [x] **RF02/RF03**: Auditoria TR × Propostas — moldes de regras + matriz de conformidade
- [x] **Auditoria (polimentos)**: editor visual de moldes + seed + tipos data/percentual/monetário
- [x] **RAG v1.0**: legislação + jurisprudência TCU/RILC (315 chunks), busca semântica, busca sem acento, diff de versões
- [x] **RF04**: Feedback/e-mail por fornecedor (endpoint + UI; requer `SMTP_HOST`/`SMTP_FROM` no `.env`)
- [x] **Correções de alto impacto (PRD v2.0)**: parsing determinístico, extração por âncoras robusta, FTS com diacríticos, schema Postgres sincronizado, paginação backward-compatible
- [x] **Copiloto LicitAI (chat consultivo)**: API + painel na tela de análise com grounding e citações (26 testes novos + 4 de schema)
- [ ] **v2.0**: Múltiplos agentes com LangGraph, checklist de conformidade, multi-usuário
- [ ] **Validação Postgres runtime**: `docker compose up -d db` quando houver Docker daemon (schema já validado por parser `pglast`)

## 📄 Licença

Uso interno — Codeba.
