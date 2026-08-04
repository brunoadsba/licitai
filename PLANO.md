# Plano do Backlog — LicitAI

Documento de planejamento para o backlog pendente do LicitAI. Organiza as tarefas em
fases priorizadas por valor, dependência e risco, com critérios de aceite e comandos de
validação. Serve de guia para agentes executarem as frentes uma a uma.

> Status das fases: `[ ]` pendente · `[~]` em andamento · `[x]` concluída
> Esforço: S (≤1h) · M (1–3h) · L (3–8h) · XL (>8h)

---

## Ordem de execução recomendada

1. **Fase 1 — Hardening (S/M)** ✅ concluída → destrava confiabilidade para tudo que vem depois.
2. **Fase 2 — Qualidade da análise (M/L)** ✅ concluída → melhora o produto principal.
3. **Fase 3 — RF04 e-mail (M/L)** ✅ concluída → fecha o ciclo da auditoria.
4. **Fase 4 — RAG v1.0 (XL)** ✅ concluída → busca semântica, jurisprudência TCU/RILC e diff de versões.
5. **Fase 5 — Auditoria polimentos (M)** ✅ concluída → novas âncoras (cnpj, prazo_relativo, cep), duplicação e dry-run.
6. **Fase 6 — v2.0 (XL)** → multi-agente (concluído) e multi-usuário.

---

## Fase 1 — Hardening do Backend

**Objetivo:** estabilidade operacional: timeout nas chamadas LLM e logging estruturado.

> **Status: [x] concluída**

### 1.1 Timeout configurável para chamadas LLM
- **Esforço:** M
- **Contexto:** `services/llm/provider.py` define `LLMProvider.generate(system, user)`.
  Não há timeout explícito hoje — chamadas podem ficar penduradas (TODO em
  `explicando-licitai.md`).
- **Tarefas:**
  1. Adicionar `llm_timeout_seconds` (ex.: 60–120s) ao `Settings` (`app/config.py`), lido do `.env`.
  2. Usar `asyncio.wait_for(provider.generate(...), timeout=settings.llm_timeout_seconds)` no `FailoverProvider.generate` (cobre todos os provedores de uma vez).
  3. Garantir que `TimeoutError` propague para o failover tentar o próximo provedor.
- **Critérios de aceite:**
  - Com timeout curto configurado no `.env`, uma chamada simulada que dorme mais que o timeout falha e o failover tenta o próximo provedor.
  - Teste unitário do `FailoverProvider` com provider lento.
- **Validação:** `pytest backend/tests/ -q` (novo teste de timeout incluído).

### 1.2 Logging estruturado JSON
- **Esforço:** M
- **Contexto:** `main.py` usa `logging.basicConfig` textual.
- **Tarefas:**
  1. Criar `app/utils/logging_config.py` com formatter JSON (timestamp, level, logger, message, exc_info).
  2. Aplicar no `main.py` e nos módulos que logam com contexto relevante.
  3. Garantir que **nenhum dado sensível** (chaves de API, conteúdo de documentos) seja logado.
- **Critérios de aceite:**
  - Logs em formato JSON válido com os campos esperados.
  - `GEMINI_API_KEY`/`GROQ_API_KEY` não aparecem em nenhum log.
- **Validação:** subir backend e verificar saída no `backend-server.log`.

---

## Fase 2 — Qualidade da Análise (produto principal)

**Objetivo:** tornar a análise juridicamente mais completa e auditável.

> **Status: [x] concluída**

### 2.1 Checklist dos elementos do Art. 6º, XXIII
- **Esforço:** M
- **Contexto:** os 10 elementos obrigatórios do TR estão documentados em
  `explicando-licitai.md` §2, mas não são forçados no prompt.
- **Tarefas:**
  1. Em `services/analyzer/prompts.py`, adicionar bloco ao system prompt listando os 10 elementos e instruindo a IA a sinalizar ausências como correção de categoria `juridica`/`estrutural`.
  2. Evitar duplicação com o fluxo DE→PARA (sinalizar, não reescrever por conta própria).
- **Critérios de aceite:**
  - Prompt contém o checklist; um TR sem "cronograma físico-financeiro" gera correção apontando a ausência.
- **Validação:** análise manual de um TR fixture + revisão do prompt.
- **Implementado:** bloco "CHECKLIST DOS ELEMENTOS OBRIGATÓRIOS DO TR (Art. 6º, XXIII)" no `SYSTEM_PROMPT` + instrução nº 4 no `ITEM_ANALYSIS_PROMPT`; testes `test_system_prompt_contem_checklist_art_6`, `test_system_prompt_sinaliza_ausencia_sem_reescrever`, `test_item_prompt_instrui_aplicar_checklist`.

### 2.2 Validação cruzada das correções pelo LLM
- **Esforço:** L
- **Contexto:** hoje cada item é analisado uma vez (`engine.py`).
- **Tarefas:**
  1. Criar prompt de revisão que recebe item + correções geradas e valida consistência (sem inventar lei, sem reduzir competitividade).
  2. Etapa pós-análise: correções marcadas como rejeitadas/ajustadas pelo revisor.
  3. Persistir status de revisão na tabela `corrections` (nova coluna) ou campo de nota.
- **Critérios de aceite:**
  - Revisor roda após análise completa e ajusta correções inconsistentes.
  - Teste unitário do novo módulo de revisão (mock não permitido — usar provider real com fixture pequena).
- **Validação:** `pytest backend/tests/ -q` + análise E2E.
- **Implementado:**
  - `services/analyzer/review.py`: `REVIEW_SYSTEM_PROMPT`/`REVIEW_PROMPT`, `review_item_corrections`, `apply_review_decisions`.
  - `engine.py`: etapa pós-análise `_run_cross_review` (rejeitadas saem do conjunto de pontuação; ajustadas têm texto/fundamento atualizados; falha de revisão mantém correções como `pendente`).
  - Colunas `review_status`/`review_note`/`reviewed_at` em `corrections` (modelo, `db/init.sql`, migração idempotente `scripts/migrate_review_columns.py`).
  - Campos expostos no `CorrectionResponse`.
  - Testes em `tests/test_analyzer.py` com providers fake implementando `LLMProvider` (sem mock).

### 2.3 Benchmark de qualidade com TRs fixture
- **Esforço:** L
- **Tarefas:**
  1. Criar conjunto de TRs fixture com "respostas esperadas" conhecidas (correções esperadas por item).
  2. Script `backend/scripts/benchmark.py` que roda a análise e mede precisão/recall.
- **Critérios de aceite:** relatório de benchmark gerado com métricas por dimensão.
- **Validação:** rodar benchmark e registrar resultado no memory.md.
- **Implementado:**
  - `scripts/benchmark_fixtures.py`: 3 TRs (omissões graves, direcionamento, adequado) com respostas esperadas por item + `LEGAL_CONTEXT` fixo (simula RAG).
  - `scripts/benchmark.py`: análise + revisão reais (LLM real, retry/backoff para rate limit, continuidade por item), métricas recall/precisão/F1 por TR e por item, contagem por dimensão; grava `backend/benchmark_report.json`.
  - **Resultado (03/08):** recall médio 0,68 · precisão média 0,89 · F1 médio 0,77. Observações: recall baixo no TR de "omissões graves" (0,375) — sinaliza lacuna na detecção de elementos ausentes; reavaliar checklist/critérios no futuro.

---

## Fase 3 — RF04: Feedback/e-mail automático por fornecedor

**Objetivo:** fechar o ciclo da auditoria enviando pendências a cada fornecedor.

- **Implementado (03/08):**
  - `app/services/comparator/feedback.py`: `montar_pendencias` (agrega `falha`/`atencao` por fornecedor, ignora `ok`) + `formatar_email_pendencias` (texto PT-BR).
  - `app/services/email/sender.py`: `smtp_configurado()`, `enviar_email` (smtplib em `asyncio.to_thread`, texto simples), `EmailConfigError`; falhas de envio capturadas por fornecedor.
  - Endpoint `POST /comparison/{comparacao_id}/feedback`: 404 se comparação não encontrada, 400 se não concluída ou SMTP ausente, retorna `{enviados, falhas, fornecedores_sem_pendencias, fornecedores_sem_email}`.
  - Config `SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD/SMTP_FROM` no `config.py` + `.env.example`.
  - Frontend (`comparacao/page.tsx` + `api.ts`): formulário de fornecedor com CNPJ/e-mail, edição e exclusão (3.1); botão **Enviar Pendências** nas comparações concluídas com resumo do resultado.
  - Testes `backend/tests/test_feedback.py` (7) — suíte total: **59 passando**.

### 3.1 Cadastro de e-mail em fornecedor
- **Esforço:** S
- **Contexto:** `Fornecedor` já tem campo `email`; CRUD e tela não expõem o campo.
- **Tarefas:**
  1. Expor `email` (e `cnpj`) no formulário de cadastro/edição (`comparacao/page.tsx`).
  2. Adicionar `updateFornecedor`/`deleteFornecedor` no `api.ts` (delete já protegido no backend).
- **Critérios de aceite:** cadastrar fornecedor com e-mail via UI persiste no banco.

### 3.2 Geração de pendências por fornecedor
- **Esforço:** M
- **Contexto:** `comparacao_resultados` guarda status por regra/fornecedor.
- **Tarefas:**
  1. Função em `services/comparator/` (ex.: `feedback.py`) que agrega resultados `falha`/`atencao` por fornecedor e monta o texto da pendência (regra, rótulo, valor esperado, valor proposto).
- **Critérios de aceite:** dado um conjunto de resultados, gera lista de pendências legível em PT-BR por fornecedor.

### 3.3 Envio de e-mail (SMTP)
- **Esforço:** L
- **Tarefas:**
  1. Config no `.env`: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`.
  2. Serviço `services/email/sender.py` (smtplib async via `asyncio.to_thread`; sem HTML rico na v1, texto simples).
  3. Endpoint `POST /comparison/{id}/feedback` que envia e-mail a cada fornecedor com e-mail cadastrado e retorna resumo de envios.
  4. **Falhas de envio não quebram a comparação** — log + resposta parcial.
- **Critérios de aceite:**
  - Endpoint envia e-mail de teste para SMTP real/descartável e retorna `{enviados, falhas}`.
  - Sem SMTP configurado → 400 com mensagem clara.
- **Validação:** teste manual com SMTP de teste + endpoint E2E.

---

## Fase 4 — RAG v1.0 (busca semântica e jurisprudência)

**Objetivo:** recuperação por similaridade com pgvector e corpus expandido.

### 4.1 Embeddings semânticos (pgvector)
- **Esforço:** XL
- **Contexto:** `legal_chunks.embedding` já existe; `retriever.py` usa FTS5 (SQLite) / ILIKE (PostgreSQL).
- **Tarefas:**
  1. Serviço `services/embeddings/` com cliente de embeddings (BAAI/bge-m3 via Ollama, ou API).
  2. Script de ingestão que calcula embeddings dos `legal_chunks` e persiste no pgvector.
  3. `retriever.py`: query por similaridade (`<=>` coseno) com fallback textual.
  4. Exige ambiente PostgreSQL/Docker (nativo é SQLite) — documentar.
- **Critérios de aceite:** busca semântica retorna chunks relevantes para consulta nova; fallback FTS5 intacto.

### 4.2 Expansão do corpus (JurisTCU + RILC)
- **Esforço:** M
- **Tarefas:**
  1. Script de ingestão para acórdãos TCU (JurisTCU) e RILC da CODEBA seguindo padrão de `ingest_laws.py`.
- **Critérios de aceite:** corpus ingerido e recuperável.

### 4.3 Comparação entre versões do TR
- **Esforço:** L
- **Tarefas:**
  1. Endpoint que recebe dois documents (TR antigo/novo) e diffs por item (número + conteúdo).
  2. Tela opcional listando alterações.
- **Critérios de aceite:** diff por item_number retorna alterado/adicionado/removido.

---

## Fase 5 — Auditoria: polimentos de usabilidade

**Objetivo:** tornar o módulo de auditoria mais produtivo.

- **5.1 Novos tipos de âncora** (CNPJ, prazo relativo, cep): adicionar ao `extractor.py` + `loader.py` + labels no frontend + testes. **Esforço:** M
- **5.2 Duplicar molde:** botão no `/moldes` que clona o molde selecionado. **Esforço:** S
- **5.3 Validar molde contra documento:** botão que roda a extração das regras sobre um TR existente e mostra quais âncoras encontraram valor (dry-run). **Esforço:** M
- **Critérios de aceite por item:** fluxo disponível na UI, testado via API.
- **Validação:** `npm run build` + `pytest backend/tests/ -q`.

---

## Fase 6 — v2.0 (multi-agente e multi-usuário)

**Objetivo:** evolução arquitetural de longo prazo.

- **6.1 Agentes LangGraph** (Jurídico, Técnico, Redação, Revisor): refatorar `analyzer/engine.py` para orquestração multi-agente. **Esforço:** XL
- **6.2 Autenticação/RBAC:** login (JWT) + controle de acesso por papel; proteger rotas. **Esforço:** XL
- **6.3 Histórico de revisões por documento:** versionamento de documentos/edições. **Esforço:** L

---

## Dependências entre fases

```
Fase 1 (hardening) ──────────►  qualquer fase (base de confiabilidade)
Fase 2.2 (revisão) ──────────►  depende de Fase 1 (timeout)
Fase 3 (RF04) ───────────────►  depende do email cadastrado (3.1); independente de RAG
Fase 4 (RAG) ────────────────►  depende de ambiente PostgreSQL/Docker
Fase 5 (polimentos) ─────────►  independente; pode rodar em paralelo
Fase 6 (v2.0) ───────────────►  depois de estabilizar 1–5
```

---

## Critérios globais de qualidade (todas as fases)

- **Código limpo PT-BR**, arquivos ≤ 200–300 linhas.
- **Sem mock em produção**; testes podem usar fixtures, mas fluxo real usa LLM real.
- Rodar sempre: `pytest backend/tests/ -q` e `npm run build`.
- Atualizar `README.md`, `explicando-licitai.md` e `memory.md` ao concluir cada fase.
- Não commitar segredos (checar com GitGuardian se disponível).
