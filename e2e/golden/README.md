# Golden Set — Régua de Confiabilidade

10 TRs anonimizados cobrirão o set final. Começamos com 3 sintéticos que travam as invariantes críticas:

- `tr_001` — TR completo com 10 elementos → checklist 100%
- `tr_002` — TR com 2 elementos faltantes → checklist deve acusar
- `tr_003` — Correções sintéticas para validar grounding (1 grounded, 1 alucinada)

Cada TR tem `document.json` (itens) e `expected.json` (correções/checklist esperado).

Teste: `pytest backend/tests/test_golden.py` — falha se precision <88% ou checklist <100%.

Para promover feedback real: `scripts/promote_feedback.py` converte thumbs-down em caso golden.
