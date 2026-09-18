# Plano — Modernização do RAG LicitAI (18/09/2026)

> Origem: pergunta “estamos usando o melhor?” + benchmarks 2026 (híbrido+rerank
> Recall@5 0.82 vs 0.70 só-híbrido; verificação por afirmação; chunks contextuais).
> Estado atual: híbrido FTS5+cosseno com RRF 0.6/0.4, top_k 4–5 direto, **sem rerank**,
> `law_numbers` existe mas o engine não usa, grounding só substring + par lei|artigo.

## Princípios (não negociáveis)

1. **Zero dependência pesada por padrão.** Nada de `torch`/`sentence-transformers`
   no requirements runtime. Rerank Fase R1 é heurístico determinístico (puro Python);
   rerank LLM é opt-in via provedor já instalado (Ollama local por padrão).
2. **Privacidade primeiro.** TR sigiloso nunca sai do host: rerank LLM usa Ollama
   local por padrão; cloud só com `LLM_ALLOW_CLOUD` + classificação não-sigilosa
   (mesma trava do `privacy.py`).
3. **Cada fase entrega sozinha** com teste verde e rollback por flag/commit.
4. **Medir antes de otimizar.** R0 congela baseline; nenhuma fase “melhora” sem número.

## Fase R0 — Harness de medida (primeiro, sem ela nada é comparável)

- Novo `backend/tests/test_rag_recall.py`:
  - Fixtures: 15–20 pares (query, chunk_ids esperados) derivados do corpus real
    (14.133, 13.303, RILC, TCU) + casos do golden (`tr_003`).
  - Métricas: Recall@5, Recall@10, MRR dos top-5.
  - O teste **documenta o baseline atual** (esperado: Recall@5 ~0.6–0.7) e falha se
    qualquer fase posterior regredir.
- Novo `scripts/eval_rag.py`: roda o harness contra Postgres piloto e imprime tabela.
- **Aceite:** suite verde; baseline registrado em `backend/rag_eval_baseline.json`.

## Fase R1 — Recuperar 20, entregar 5 + filtro por regime (maior ganho, ~2 dias)

Arquivos:
- `backend/app/services/rag/rerank.py` (novo, puro, ≤120 LOC):
  - `heuristic_rerank(query, rows) -> rows` — score = 0.5·RRF + 0.25·overlap de termos
    (boundary, normalizado) + 0.15·bônus regime (lei da query casa com chunk) + 0.10·bônus artigo (nº do artigo da query presente no chunk).
  - Determinístico, sem IO/LLM, testável.
- `backend/app/services/rag/retriever.py`: `retrieve()` passa a buscar
  `candidates = max(top_k*4, 20)` em cada backend, funde via RRF existente,
  aplica `heuristic_rerank` e devolve `top_k`. Flags em `config.py`:
  `rag_candidates=20`, `rag_top_k=5`, `rag_rerank_mode="heuristic"`, `rag_regime_filter=1`.
- `backend/app/services/analyzer/analysis_phases.py::_retrieve_legal_context`:
  passa `law_numbers` do regime detectado (`detect_regime` do evidence_gate) quando
  `rag_regime_filter=1` e regime não-ambíguo.
- Testes: `test_rerank.py` (casos [0]/[10] do precision: chunk certo sobe ao top-5),
  `test_rag_recall.py` deve **subir** vs baseline (meta: Recall@5 ≥ baseline+0.08).
- **Aceite:** Recall@5 sobe sem queda de precisão no golden; custo LLM zero;
  rollback = `rag_rerank_mode="off"`.

## Fase R2 — Chunks contextuais (reingestão versionada, ~2 dias)

- Problema: embedding só do texto solto; “Art. 6” de leis diferentes colidem.
- `backend/scripts/ingest_*.py` + `ingest_embeddings.py`: prefixar cada chunk com
  cabeçalho `"{law_number} — {article} — {section}\n"` antes de embedar
  (texto exibido continua igual; só o vetor muda). `embedding_dim` versionado por
  chunk (já existe coluna) + `corpus_version` no snapshot (`legal-v2`).
- Compatibilidade: `_assert_query_dim` já bloqueia dim incompatível; reingestão é
  idempotente; Postgres piloto e SQLite dev reingeridos em sequência (nunca paralelo).
- **Aceite:** `test_golden_grounding_pairs` verde; Recall@5 sobe de novo ou ao menos
  empates de lei somem nos logs; rollback = reingestão do corpus antigo (scripts idempotentes).

## Fase R3 — Rerank LLM opt-in + taxa de suporte por afirmação (~3 dias)

- `backend/app/services/rag/rerank.py`: `llm_rerank(query, rows, llm)` — prompt
  compacto “nota 0–2 por relevância”, 1 chamada por query sobre os top-10
  heurísticos, devolve top-5. Ativo só com `rag_rerank_mode="llm"`.
- Provedor: `get_llm_provider()` comFailover existente; **default Ollama local**;
  cloud bloqueado para doc sigiloso (`assert_cloud_allowed_for_document`).
  Custo: +1 chamada LLM por item (compensa: R1 já cortou ruído; teto
  `ANALYSIS_MAX_LLM_CALLS` passa a contar rerank como 0.25 chamada ou entra no
  modo economic com top_k menor — decisão na implementação, documentada).
- `claim_support_rate` em `evidence_gate.py`: quebrar correção em afirmações
  (trecho, cada número, fundamento) e exigir suporte individual; expor
  `evidence.claims_supported/total` persistido no `evidence` JSON da Correction.
- UI mínima: selo “2/3 afirmações ancoradas” no `CorrectionCard` (reuso do banner).
- **Aceite:** taxa de suporte ≥0.9 no golden; nenhum chunk cloud em doc sigiloso
  (teste `test_rag_privacy.py`); rollback = `rag_rerank_mode="heuristic"`.

## Fase R4 — Avaliação, rollout e docs (~1 dia)

- `scripts/eval_rag.py` final: Recall@5/10, MRR, claim-support médio, precision do
  golden — tabela antes/depois por fase em `backend/rag_eval_report.md`.
- Quinzena: re-rodar `score_art6_fixtures.py` + 1 análise ouro (09-ti-pabx-nuvem)
  e registrar precisão nova.
- Docs: README (RAG v2), `docs/ops/piloto.md` (linha RAG), `memory.md`,
  `.env.example` (`RAG_*`).
- **Aceite:** relatório com números; nenhuma regressão (283+ testes verdes);
  decisão go/no-go do rerank LLM no piloto baseada em custo real.

## Fora de escopo (não fazer agora)

Grafo de conhecimento jurídico, reescrita de query genérica/HyDE/RAG-Fusion
(ganho ~zero nos benchmarks), `torch`/`sentence-transformers` no runtime,
troca de embedding provider, K8s, multi-tenant.

## Ordem de execução

R0 → R1 (maior ganho, quase zero custo) → R2 → R3 → R4.
Cada fase validada pela régua antes da próxima.
