# Fixtures TR CODEBA (local)

Base de Termos de Referência reais para piloto, benchmark quinzenal e Diff.

**PDFs não entram no Git** (ver `.gitignore`). Só este README e a estrutura de pastas são versionados.

## Estrutura

```
fixtures/trs-codeba/
├── piloto-unico/     # 1 PDF por objeto (canônico do piloto) — hardlinks
├── objetos/          # todos os arquivos, com versões
│   ├── 01-agua-mineral/
│   ├── 02-materiais-domo-sanitarios/
│   ├── 03-locacao-conteineres/
│   ├── 04-parceria-codeba-cimatec/
│   ├── 05-concurso-guarda-portuario/   # v01..v03
│   └── 06-base-emergencia-operacional/ # v01..v03 + alt
└── pendente/         # lacunas até 10+ objetos distintos
    ├── 07-obra-engenharia/
    ├── 08-servico-continuo/
    ├── 09-ti-software/
    └── 10-tr-incompleto-minimo/
```

## Convenção de nomes

| Padrão | Uso |
|--------|-----|
| `vNN-sei-<id>-tr-projeto-basico.pdf` | Versão SEI numerada do mesmo processo |
| `alt-*.pdf` | Formato alternativo (não-template SEI) |
| `piloto-unico/NN-slug.pdf` | Canônico do objeto `NN` |

Ao adicionar TR novo: criar `objetos/NN-slug/`, colocar `v01-...pdf`, e se for set piloto, hardlink em `piloto-unico/`.

## Set piloto atual (6/10)

Ver [MANIFEST.md](MANIFEST.md). Faltam os tipos em `pendente/`.

## Uso

1. Benchmark quinzenal: enviar os PDFs de `piloto-unico/` (modo economic).
2. Diff / Atualizar TR: usar `v01` → `v02` → `v03` em Guarda ou Emergência.
3. Anonimizar e-mail/telefone/CPF antes de free-tier cloud.

## Segurança

- Não commitar PDFs.
- Preferir TRs já públicos ou anonimizados.
- Pasta antiga `Base de Dados com TR para teste/` foi migrada para cá.
