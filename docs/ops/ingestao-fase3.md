# Ingestão confiável (Fase 3)

Pipeline jurídico com estágios separados: source → extract → normalize → validate → version → index.

- Hash SHA-256 da fonte; duas corridas iguais mantêm o mesmo `legal_documents.id` e os mesmos chunks.
- Origem, URL, data de coleta e manifesto em `legal_documents`.
- Tachado, `(VETADO)` e `(Redação dada pela…)` saem estruturados; histórico não entra no texto vigente.
- Documento incompleto (sem artigo/conteúdo) fica `ingest_status=failed` e não é publicado.
- Reprocessar a mesma `law_number` republica se a fonte passar na validação.
- Upload de TR/proposta só grava o arquivo e enfileira job `parse`. O worker faz parse/OCR.
- OCR tem timeout hard que envia SIGKILL ao processo filho.
- Falha de parse do upload: `POST /documents/{id}/reparse`.

Schema: `20260924_002`. Depois de puxar a branch, aplicar a migration e reiniciar API/worker juntos.

> Lock de ingestão: rodar `ingest_*` sempre **sequencial no mesmo banco** — nunca paralelizar duas ingestões (corrompe `corpus_version` e duplicatas de chunk).

```bash
# no host, com Compose no ar
docker compose exec backend alembic upgrade head
```

Não reative CI no GitHub sem pedido explícito.
