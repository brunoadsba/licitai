# Fixtures TR CODEBA (local)

Base de Termos de Referência reais para piloto, benchmark quinzenal e Diff.

**PDFs não entram no Git** (ver `.gitignore`). Só README/MANIFEST e a estrutura de pastas são versionados.

## Estrutura

```
fixtures/trs-codeba/
├── piloto-unico/     # 1 PDF por objeto (canônico) — hardlinks · 12 arquivos
├── objetos/          # todos os arquivos, com versões (01…12)
└── pendente/         # só candidatos ainda não classificados
```

## Convenção de nomes

| Padrão | Uso |
|--------|-----|
| `vNN-sei-<id>-tr-projeto-basico.pdf` | Versão SEI numerada do mesmo processo |
| `alt-*.pdf` | Formato alternativo (não-template SEI) |
| `piloto-unico/NN-slug.pdf` | Canônico do objeto `NN` |

Ao adicionar TR novo: criar `objetos/NN-slug/`, colocar `v01-...pdf`, hardlink em `piloto-unico/`, atualizar MANIFEST.

## Set piloto

**12 objetos distintos** (meta ≥10 atingida). Detalhes: [MANIFEST.md](MANIFEST.md).

Lacunas antigas preenchidas em 10/09/2026:
- obra → `07-obra-portaria-salvador`
- contínuo → `08-coleta-residuos-perigosos`
- TI → `09-ti-pabx-nuvem`
- cobertura Art.6 mais enxuta → `10-monitoramento-ambiental-pga`
- extras → `11-compra-epi-epc`, `12-coletores-sobre-demanda`

## Uso

1. Benchmark quinzenal: 5 TRs de `piloto-unico/` (rodízio entre os 12).
2. Diff / Atualizar TR: `objetos/05-…` e `06-…` (`v01`→`v02`→`v03`).
3. Anonimizar e-mail/telefone/CPF antes de free-tier cloud.

## Segurança

- Não commitar PDFs.
- Preferir TRs já públicos ou anonimizados.
