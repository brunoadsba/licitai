# Modelo jurídico versionado (Fase 4)

Sidecar de `legal_works` / `legal_versions` / `legal_provisions`. O índice legado (`legal_documents` + `legal_chunks`) continua servindo a busca.

- Versões publicadas são imutáveis. Fonte nova com outro hash cria versão e marca a anterior `superseded`.
- Busca padrão do modelo novo: versão `published` e dispositivo `vigente`. Histórico só com `include_historical=True`.
- TCU em quarentena gera versão `unpublished` e não entra na consulta vigente.
- `legal_id_map` liga `legal_chunks.id` ao dispositivo do artigo.
- Amostra: `PYTHONPATH=. python scripts/migrate_legal_sample.py` (Lei 14.133 e 13.303).

Schema: `20260924_003`. Aplicar migration e reiniciar API/worker juntos.

Visto de uma amostra por curador jurídico: **pendente** (humano).
