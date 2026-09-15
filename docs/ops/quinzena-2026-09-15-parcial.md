# Quinzena Art.6 — parcial 15/09/2026 (heurística, sem LLM)

Comando: `PYTHONPATH=backend python3 backend/scripts/score_art6_fixtures.py --dir fixtures/trs-codeba/piloto-unico`

## 5 TRs do rodízio

| TR | Cobertura | Faltantes típicos |
|----|-----------|-------------------|
| 07-obra-portaria-salvador | 90% OK | `descricao_solucao` |
| 11-compra-epi-epc | 80% | `descricao_solucao`, `adequacao_orcamentaria` |
| 01-agua-mineral | 70% | `fundamentacao`, `descricao_solucao`, `adequacao_orcamentaria` |
| 05-concurso-guarda-portuario | 40% | `fundamentacao`, `descricao_solucao`, `requisitos`, `modelo_gestao`, `selecao_fornecedor`, `adequacao_orcamentaria` |
| 09-ti-pabx-nuvem | 100% OK | — |

**Média 5 TRs: 76% · ≥90%: 2/5** — igual ao baseline de 14/09 (`docs/ops/quinzena-2026-09-14.md`).

## Piloto completo (12 objetos)

**Média: 71% · ≥90%: 2/12.** Lacunas sistêmicas: `descricao_solucao` (solução como um todo, 11/12) e `adequacao_orcamentaria` (10/12); depois `fundamentacao` (6/12). São gaps de curadoria dos TRs — não do validador. Cobertura LLM da análise real do 09 (Fase 1) deu 100%, acima da heurística.
