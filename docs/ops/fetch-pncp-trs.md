# Spike PNCP — runbook (28/09/2026)

Baixa TRs/Projetos Básicos **públicos** da CODEBA via API de consulta do PNCP
(sem token). Sem LLM, sem worker, sem upload.

## Dry-run (só lê, nada grava)

```bash
PYTHONPATH=backend python backend/scripts/fetch_pncp_trs.py --de 20240101 --ate 20260928
```

Saída: nº de contratações, nº de arquivos TR/PB, **tipos de documento vistos**
(validar `tipoDocumentoId` 4/6 ao vivo antes de confiar no filtro), e a
`razaoSocial` retornada (confirma que o CNPJ é mesmo o da CODEBA).

CNPJ default: matriz `14372148000161`. `--cnpj` repetível p/ filiais
(Salvador/Ilhéus/Aratu — confirmar os 14 dígitos antes de usar; só após o
dry-run da matriz).

## Apply (grava PDF + manifesto)

```bash
PYTHONPATH=backend python backend/scripts/fetch_pncp_trs.py \
  --de 20240101 --ate 20260928 --apply --max-downloads 50
```

Destino: `fixtures/trs-codeba/pendente/pncp/` (gitignored p/ PDF) +
`manifest.jsonl` (versionável: cnpj/ano/seq/tipo/título/url/sha256).
Dedupe por URL e por hash. Nome: `{ano}-{seq}-{tr|pb}-{slug}.pdf`.

## Depois do apply

1. Triagem humana: conferir `tipoDocumentoId` reais, checar **PII/LGPD**,
   mover úteis p/ `objetos/NN-slug/` + MANIFEST. Nada vai sozinho p/ piloto.
2. Anonimizador (`backend/scripts/anonymize_emergencia.py`) só se a triagem
   achar dado pessoal.

## Rate limit (aprendido 28/09)

O PNCP bloqueia IP apressado por minutos ( tomei bloqueio testando).
CLI usa pausa 1,5s + backoff exponencial c/ jitter; se travar, esperar e
retomar (manifesto permite recomeçar sem duplicar).

## Resultado dry-run 28/09 (matriz 2024–2026)

- CNPJ confirmado: `COMPANHIA DOCAS DO ESTADO DA BAHIA`.
- **20 contratações, 0 arquivos TR/PB** — tudo `tipoDocumentoId 2 (Edital)`.
- Janela >1 ano dá 422: CLI fatia por ano (`janelas_anuais`).
- Conclusão honesta: poço seco p/ TR avulso na matriz. TR pode vir como
  anexo dentro do Edital (fora deste spike). Filiais inexploradas, mas o
  padrão de publicação deve ser o mesmo.
