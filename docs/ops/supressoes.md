# Supressões — inventário (25/09/2026)

21 ocorrências (`noqa` / `as any` / `ts-ignore`). Regra: remover o gratuito; o resto vira issue com dono.

## Legítimas (manter)

| Arquivo | Regra | Motivo |
|---------|-------|--------|
| `backend/app/main.py:40-52` | `noqa: F401` | Registro de metadata no `create_all` (SQLite dev/teste) |
| `backend/app/worker.py:25` | `noqa: F401` | Registro de metadata |
| `backend/app/services/rag/retriever.py:18-35` | `noqa: F401` | Re-export — contrato de monkeypatch em testes |
| `backend/app/models/analysis.py:201`, `comparison.py:169`, `legal.py:98` | `noqa: E402,F811` | Import tardio / re-export de modelo versionado |
| `backend/app/services/analyzer/prompts.py:110` | `noqa: E402` | Import após definição de prompt (intencional) |

## Revisar (candidatas a remoção)

| Arquivo | Regra | Ação |
|---------|-------|------|
| `rules/llm_fallback.py:79`, `reviewer/second_opinion.py:67`, `comparator/feedback.py:156` | `noqa: BLE001` | `BLE` nem está no `select` do ruff — supressão inócua; remover ou habilitar `BLE` no `pyproject` e tratar |
| Frontend `as any` / `ts-ignore` (se existirem em `src/`) | — | Auditar um a um; trocar por tipo estreito ou `unknown` + narrowing |

Comando de re-auditoria:

```bash
grep -rn "noqa\|as any\|ts-ignore\|ts-expect-error" backend/app frontend/src --include="*.py" --include="*.ts" --include="*.tsx"
```
