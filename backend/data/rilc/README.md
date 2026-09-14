# RILC CODEBA (corpus RAG)

## Fonte canônica

- Manifesto: [`source/provenance.json`](source/provenance.json)
- PDF local (gitignored): `source/rilc-codeba-rev1-2022-03-31.pdf`
- URL canônica CODEBA (atos normativos): ver `url_canonica` no manifesto
- Espelho (mesmo hash): `url_espelho`

## Ingestão

Na pasta `backend/` (Postgres do Compose ou SQLite local):

```bash
unset POSTGRES_PASSWORD DATABASE_URL   # se Compose no WSL
PYTHONPATH=. python scripts/ingest_rilc_codeba.py
# opcional: embeddings
PYTHONPATH=. python scripts/ingest_embeddings.py
```

O script:
1. Garante o PDF local (usa o arquivo ou baixa canônica/espelho)
2. Valida SHA-256 contra o manifesto
3. Extrai texto página a página (`pdfplumber`) com marcadores `# Página N`
4. Ingere por artigo via `ingest_law_text` (`law_number=RILC-CODEBA`)
5. Remove o stub legado `RILC-CODEBA-2023` se existir
6. Reconstrói FTS (SQLite) e faz commit

## Arquivos

| Path | Uso |
|------|-----|
| `source/provenance.json` | Metadados + hash pinado (versionado) |
| `source/*.pdf` | Binário oficial (não versionar) |
| `amostra.txt` | Stub antigo — **não** usar para RAG; mantido só como referência histórica |
