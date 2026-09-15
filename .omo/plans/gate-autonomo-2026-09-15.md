# Plano — Trabalho Autônomo do Gate 15/09/2026 (sem depender do Bruno)

> Branch: `chore/gate-autonomo-15-09` (base `main` `1737ab3`).
> Invariantes: single-user, 1 worker, dado CODEBA sigiloso fica local, CI desabilitado,
> gate 14d até 28/09 com métricas comparáveis. Nada sai do host; nada vai para cloud.
> Julgamento humano (aprovar/rejeitar alto-crítico, SEI real, Solange, secrets) fica com o Bruno.

## Objetivo

Executar sozinho, em ordem de valor, o que destrava o gate sem o Bruno:
re-upload + reanálise do TR de TI, benchmark heurístico Art.6, mapa de e-mails da
Emergência (só leitura), dry-run do `promote_feedback` e spike de `art6_coverage`
isolado sem merge.

## Fase 0 — Trava (15 min)

1. Stack de pé: `./scripts/up.sh` (sem `--build` salvo se imagem defasada) + `./scripts/smoke_readyz.sh`.
2. Congelar `ANALYSIS_MAX_LLM_CALLS=24`, `ANALYSIS_CONCURRENCY=1`, 1 worker no Compose.
3. Baseline: `PYTHONPATH=backend python3 -m pytest backend/tests -q` → anotar (esperado 265).
4. Critério de saída: 4 containers healthy + baseline verde anotada no relatório.

## Fase 1 — Re-upload + reanálise `09-ti-pabx-nuvem` (~20 min, LLM real)

- Arquivo: `fixtures/trs-codeba/piloto-unico/09-ti-pabx-nuvem.pdf` (parser pós-14/09; re-upload limpa itens de sumário antigos).
- Passos (stack local, modo `economic`):
  1. `POST /documents/upload` com o PDF → `document_id` (novo documento; o antigo com itens de sumário fica para comparação, não é apagado).
  2. Aguardar `parsed` (poll `/documents/{id}`).
  3. `POST /analysis/{id}/start` (`{"mode":"economic"}`) → worker processa (~10–15 min, sessão ouro: 778 s).
  4. Poll até `completed` ou `completed_with_errors`; coletar: duração, `analyzed_item_ids`/`budget_truncated`/`failed_item_ids`, `art6_coverage`, `score_overall`/`risk_level`.
  5. Baixar `sei-pack`, `corrected-html`, `corrected-docx` e conferir 200 + tamanho > 0.
- Entrega: `docs/ops/gate-reanalise-09-ti-2026-09-15.md` (ids, tempos, status, cobertura, artefatos ok/falha).
- Aceite: análise termina (mesmo que `completed_with_errors`) com snapshot coerente; relatório pronto para o Bruno revisar alto/crítico.
- Risco: cota free tier 429 estoura os ~15 min → retry com backoff; se zerar, anotar e reagendar (não é regressão).

## Fase 2 — Benchmark heurístico Art.6, 5 TRs (~15 min, sem LLM)

- Script: `backend/scripts/score_art6_fixtures.py` (heurística PDF, sem cota).
- TRs: `07-obra-portaria-salvador` → `11-compra-epi-epc` → `01-agua-mineral` → `05-concurso-guarda-portuario` (+ `09-ti-pabx-nuvem` já medido na Fase 1).
- Entrega: tabela por TR (`coverage`, alíneas faltantes típicas) + média vs baseline 76% em `docs/ops/quinzena-2026-09-15-parcial.md`.
- Aceite: 5/5 medidos, sem tocar no banco do piloto; diff contra `docs/ops/quinzena-2026-09-14.md` explicado em 5 linhas.

## Fase 3 — Mapa de e-mails da Emergência (só leitura)

- Alvo: `fixtures/trs-codeba/objetos/` + `piloto-unico/06-base-emergencia-operacional.pdf` (PDFs gitignored; nenhum é modificado).
- Passos: extrair texto via parser local (PyMuPDF, sem LLM, sem rede) → regex de e-mail → contar por arquivo.
- Entrega: tabela (arquivo × nº e-mails mascarados como `***@***`) + esqueleto de script `backend/scripts/anonymize_emergencia.py` em modo `--dry-run` (lista o que trocaria, não escreve nada).
- Aceite: nenhum PDF alterado (`git status` limpo em `fixtures/`); execução real só com ok explícito do Bruno.
- Proibido: enviar qualquer trecho para cloud; log com PII (usar `pii_scrub`).

## Fase 4 — Dry-run do `promote_feedback` (sem dado real)

- Script: `backend/scripts/promote_feedback.py` com stub sintético em `e2e/golden/feedback/` (thumbs-down fake, sem TR real).
- Entrega: log do dry-run + checklist (stub → golden ok/falha e motivo).
- Aceite: pipeline validado de ponta a ponta sem tocar em feedback real; nenhum stub real criado.

## Fase 5 — Spike `art6_coverage` ISOLADO (não mergear até 28/09)

- Escopo: cópia de trabalho em branch separada `spike/art6-coverage-15-09` (a partir desta branch); arquivos candidatos: `services/legal/art6_xxiii.py`, `services/analyzer/prompts.py`, agente estrutural, fallback `/gerar-tr`.
- Proibido: merge em `main` ou nesta branch antes de 28/09 (muda a régua do gate e invalida as métricas da Fase 2).
- Entrega: diff + antes/depois no golden FakeLLM (precision ≥ 0.88 mantida) + recomendação (merge pós-gate ou descarte).
- Aceite: relatório comparativo; zero alteração em `main`.

## Verificação por fase

- Fase 0: `./scripts/smoke_readyz.sh` ok + `pytest backend/tests -q` 265.
- Fase 1: análise com `analysis_id` + duração + `art6_coverage` + 3 artefatos HTTP 200.
- Fase 2: tabela 5 TRs + média.
- Fase 3: `git status --porcelain fixtures/` vazio + tabela de contagem.
- Fase 4: dry-run ok sem stubs reais.
- Fase 5: branch spike separada + relatório; `git log main` intocado.

## Riscos e não-escopo

- Não: julgamento alto/crítico, SEI real, Solange, rotação de secrets, cloud com TR real, free-tier com CODEBA, CI, K8s/Redis, multi-tenant, fine-tune, multi-worker, migração Alembic nova.
- LLM 429/cota: reagendar Fase 1, nunca forçar com provider sem crédito.
- Qualquer achado que mude a régua do gate → Fase 5 (spike), nunca direto em `main`.

## Ordem de execução

Fase 0 → Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fase 5 (spike) → relatório final + `memory.md` §5/§8.
