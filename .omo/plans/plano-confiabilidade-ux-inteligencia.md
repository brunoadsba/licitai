# Plano — Confiabilidade da Informação + UX Simplificada + Inteligência Core

**Objetivo:** levar o LicitAI de **8.2 → 9.0+** como piloto single-user free. **Confiabilidade aqui = fidelidade do que o sistema diz:** cada correção aponta problema real, cada fundamento existe no corpus, cada TR gerado cumpre a lei e não inventa.

> Base: hardening recém entregue (13 commits, 180 unitários verdes, E2E 15/17, restore fiel, FKs, request-id). O hardening foi de infra; este plano é de **conteúdo**.

---

## Princípios (piloto free)

1. **Determinístico primeiro, LLM depois.** Extrair com regex/âncora; só chamar LLM quando a regra não é ancorável. Toda saída de LLM é validada contra dado real antes de mostrar.
2. **Toda afirmação é rastreável.** Correção → `original_text` no documento + `legal_basis` no corpus + `confidence`. Sem citação = recusa, não invenção.
3. **TR é documento legal, não texto bonito.** Geração segue checklist dos 10 elementos do Art. 6º XXIII + molde configurado; desvio = erro, não criatividade.
4. **Humano decide, máquina sugere.** `review_status` (pendente/aprovada/rejeitada) e importância são filtro obrigatório, não detalhe.

## Métricas de sucesso (4 semanas após entrega)

| Pilar | Métrica | Hoje | Alvo |
|---|---|---|---|
| **Informação — Análise** | Precision de correções (correção aponta falha real) | ~70% estimado, sem golden set | **>88%** em golden set de 10 TRs |
| **Informação — Grounding** | Correções com `legal_basis` válido no corpus / total | ~75% | **>95%** |
| **Informação — TR gerado** | Conformidade checklist 10 elementos (estrutural agent passa) | não medido | **100%** dos 10 elementos presentes |
| **Informação — Alucinação** | Trechos `suggested_text` sem ancoragem no documento | desconhecido | **<3%** |
| **UX** | Tempo upload → 1ª correção copiável pro SEI | ~2,5 min, 5 cliques | **<90s, 3 cliques** |
| **Custo** | Tokens médios / análise | baseline | **-30%** mantendo precision |

---

## Dores de informação mapeadas

- **Parser/extração:** `docx_parser`/`pdf_parser` extraem `item_number/title/content` mas sem validação de completude; tabelas viram `item_type=table` sem normalização → correções perdem contexto.
- **Regras:** 10 âncoras (numérica, extenso, booleana, legal, data, percentual, monetária, CNPJ, prazo relativo, CEP) com fallback LLM não calibrado → `extrair_valor` retorna `None` e o comparador classifica como `atencao` sem explicar se é ausência real ou falha de extração.
- **Análise:** 4 agentes + revisão cruzada existem, mas `sanitize_correction` só valida formato; não valida se `legal_basis` existe no `legal_chunks` nem se `original_text` é substring do item. Score clampado, mas `generate_scores` ainda depende só de LLM sem calibração contra severidade real.
- **TR gerado:** `tr_builder` monta HTML a partir de prompt único sem validação contra os 10 elementos nem contra molde; `generateTR` não registra `prompt_version` nem `corpus_version` → irreprodutível.
- **UX da confiança:** usuário vê lista de correções sem saber quais são determinísticas vs LLM, nem grau de confiança → trata tudo igual.

---

## Pilar 1 — Confiabilidade da Informação (semana 1-2)

### C1. Rastreabilidade ponta-a-ponta
- **O quê:** Cada `Correction` passa a carregar `evidence: { item_id, excerpt_hash, legal_chunk_ids, extractor: 'ancora'|'llm', prompt_version, corpus_version }`. `tr_builder` grava `generation_manifest` no `Document` (molde_id, prompt_version, corpus_version, análise origem).
- **Por que:** Reproduzir "por que essa correção apareceu" sem log é impossível. Hash do excerto prova que `original_text` veio do documento.
- **Validação:** `GET /report/{id}` retorna `evidence`; teste de regressão: re-gerar TR com mesmo manifest → hash idêntico.

### C2. Validação de grounding (anti-alucinação)
- **O quê:** Novo `validator/grounding.py` usado por `engine` e `generator`: (a) `original_text` deve ser substring normalizada do `item.content` (tolerância a whitespace), senão `review_status=rejeitada`; (b) `legal_basis` deve casar `law_number + art` existente em `legal_documents`, senão `importance` rebaixada e `legal_basis=None`.
- **Esforço:** Médio. **Risco:** Baixo (rejeita só o que já era alucinação).
- **Validação:** Golden set: injetar `legal_basis` falso → teste espera rejeição.

### C3. Extração em 2 camadas com confiança
- **O quê:** `extractor.py` já separa âncora determinística vs `llm_fallback.py`. Adicionar `confidence` (1.0 âncora exata, 0.6 LLM) e `reason` ("âncora 'vigência' a 12 chars do número"). Comparador usa `confidence <0.7 → status=atencao + motivo="extração incerta"` em vez de `falha` seca.
- **Validação:** `test_extractor.py` com 10 casos por tipo de âncora + 1 caso LLM mockado.

### C4. Checklist legal do TR gerado
- **O quê:** `StructuralAgent` já tem checklist dos 10 elementos; reutilizar como **validador pós-geração** em `tr_builder`: após `generate`, roda `validate_tr_completeness(html)` → se faltar elemento, re-prompta só o bloco faltante (não re-gera tudo).
- **Esforço:** Médio.
- **Validação:** Gerar TR com `objeto` vazio → falha de validação com `elemento_faltante: 'objeto'`.

### C5. Calibração de severidade e nota
- **O quê:** Hoje `severity` vem do LLM sem ancoragem. Adicionar regra: `critico` só se `category=juridica` + `legal_basis` válido + `confidence>=0.7`; senão rebaixa para `alto`. `sanitize_scores` já clampado; adicionar peso por `critico` validado (não por contagem bruta).
- **Validação:** Teste com 3 correções `critico` sem fundamento → nota não despenca para 2.0.

### C6. Golden set de informação
- **O quê:** `e2e/golden/` com 10 TRs reais anonimizados: cada um tem `expected_corrections.json` (categoria/severidade/trecho) e `expected_tr_checklist.json`. Novo `pytest tests/test_golden.py` roda `run_analysis` com `FakeLLM` determinístico + `test_golden_tr.py` que gera TR e valida checklist. Falha se precision <88% ou checklist <100%.
- **Por que antes de otimizar:** sem régua, otimização de custo (cache/compressão) pode derrubar qualidade sem perceber.
- **Ordem C:** C2 → C3 → C1 → C5 → C4 → C6 (C6 fecha a régua, mas pode começar com 3 TRs já na semana 1)

---

## Pilar 2 — UX Simplificada (semana 2-3)

### UX1. Wizard de 3 passos (corta navegação)
```
[1 Escolher TR] → [2 Ver correções filtradas] → [3 Copiar pro SEI em 1 clique]
```
- Passo 1: DropZone única; já filtra `Crítico/Alto` por padrão (onde está o risco).
- Passo 3: **Botão único** por correção: `Copiar Item Corrigido` → clipboard = `PARA: <suggested_text>\nFundamento: <legal_basis> — <snippet>\nJustificativa: <justification>\nConfiança: <confidence>` + toast com `request-id` copiável.

### UX2. Dashboard essencial
- 3 cards fixos: `Recentes (3)`, `Em análise`, `Pendências por fornecedor`. Resto em `Ver todos`. Empty state com CTA `Enviar primeiro TR`.

### UX3. Moldes com templates
- 3 templates (Geral, Continuados, Obras) preenchem `config_json`; `Dry-Run` inline mostra `valor_extraido + confidence` ao lado de cada regra.

**Validação UX:** 5 usuários internos: fixture → cópia SEI <90s.

---

## Pilar 3 — Inteligência Core Enxuta (semana 3-5)

### I1. Cache de contexto jurídico
- Hash da query → 4 chunks; TTL 1h → -40% buscas em TR de 20 itens.

### I2. Prompt compression
- `8000 → 4000` chars + sumário de 200 tokens; prompts versionados em `prompts/v2/` com teste contra golden set.

### I3. RAG tuning
- Grid search `top_k` e pesos RRF (0.6 semântico / 0.4 textual) medindo `recall@5` no golden set.

### I4. Orquestração econômica
- Early exit: se 2 agentes retornam 0 correções com confiança alta, pula os outros 2. Provedor por etapa: Groq rápido p/ extração, Gemini 1.5 p/ fundamentação.

### I5. Custo visível
- Log `llm_usage` já existe; expor `tokens / análise` no `ReportResponse` e no dashboard.

---

## Roadmap incremental

```
Semana 1 : C2 (grounding) + C3 (confiança) + UX4 (cópia SEI)     → corta alucinação, valor imediato
Semana 2 : C1 (rastreabilidade) + C5 (calibração) + UX1 (wizard) → confiança explicável + fluxo simples
Semana 3 : C4 (checklist TR) + C6 (golden 3 TRs) + I1 (cache)    → TR confiável + régua
Semana 4 : I2 (compressão) + I4 (orquestração)                   → -30% custo
Semana 5 : I3 (RAG tuning) + C6 completo (10 TRs)                → 88%+ precision
```

Cada semana: `pytest 180 + next build + 11 E2E determinísticos` verdes + `pytest tests/test_golden.py` não regride.

## Fora de escopo

Multi-tenant, RBAC, K8s, fila externa, fine-tune, troca de ORM.

## Próximo passo

Aprovar → quebro Semana 1 (C2+C3+UX4) em 3 commits atômicos e entrego com `test_golden` inicial (3 TRs).
