# Qualidade do piloto CODEBA (sem LLM paga)

**Status:** procedimento escrito; **execução quinzenal pendente** (Bruno / elaboradores).

Rotina quinzenal para manter precision em **alto/crítico** e Art. 6º.

## Checklist quinzenal

1. Selecionar 5 TRs reais anonimizados (sem dados pessoais/sigilosos desnecessários).
2. Rodar análise em modo **economic** (padrão do upload).
3. Anotar:
   - taxa de rejeição humana em correções `alto|critico`
   - gaps Art. 6º (painel a–j)
   - uso de **pacote SEI** ou **TR HTML** vs cópia avulsa
   - ocorrências de `completed_with_errors`
4. Opcional: `PYTHONPATH=backend python backend/scripts/benchmark.py` (gasta cota free tier).
5. Thumbs-down do copiloto → stub em `e2e/golden/feedback/` → promover:

```bash
PYTHONPATH=backend python backend/scripts/promote_feedback.py --list
PYTHONPATH=backend python backend/scripts/promote_feedback.py --stub PATH --dry-run
# após curadoria humana:
PYTHONPATH=backend python backend/scripts/promote_feedback.py --stub PATH --apply
```

Stubs podem incluir `approved_corrections: [...]` para pré-preencher `expected_findings` (flag `needs_human_curation` permanece).

## Após pin de modelo

```bash
./scripts/smoke_llm.sh
# opcional (1 chamada real):
LLM_SMOKE_REAL=1 ./scripts/smoke_llm.sh
```

Não trocar modelo sem smoke. Evitar aliases `*-latest` sem validação.
