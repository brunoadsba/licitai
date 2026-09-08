# Golden Set — Régua de Confiabilidade

Meta: **≥10 TRs** sintéticos/anonimizados; precision ≥ **0.88**, recall ≥ **0.80**.

Preditor: FakeLLM determinístico em `backend/app/services/analyzer/fake_llm_golden.py`
(não copia `expected_findings`).

| Fixture | Papel |
|---------|--------|
| tr_001 | Completo a–j |
| tr_002 | Faltam i/j |
| tr_003 | Grounding + gaps |
| tr_004 | Marca exclusiva |
| tr_005 | Prazo ambíguo |
| tr_006 | Direcionamento |
| tr_007 | Mínimo (muitos gaps) |
| tr_008 | Marca + prazo + gaps |
| tr_009 | Prompt injection (0 findings) |
| tr_010 | FP deliberado do FakeLLM |

```bash
cd backend && PYTHONPATH=. pytest tests/test_golden.py -q
```

Feedback thumbs-down → stub em `feedback/`; promover com:

```bash
PYTHONPATH=backend python backend/scripts/promote_feedback.py --list
PYTHONPATH=backend python backend/scripts/promote_feedback.py --stub PATH --apply
```
