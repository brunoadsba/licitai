# Anotação PABX — fechada (28/09/2026)

Placar: **0 aprovar, 17 rejeitar.** Precisão > recall. Prova: PDF
`fixtures/trs-codeba/piloto-unico/09-ti-pabx-nuvem.pdf` passado pelo parser
do projeto (`parse_pdf` + `structure_items`). O campo `content` de cada item
está completo. O que a máquina leu como título truncado é a primeira linha
do PDF, cortada na quebra de linha.

Os 3 TPs já carimbados por humano (3.1.1, 3.1.2, 3.1.4, keyword
"abruptamente") **não foram reabertos**. O mesmo padrão de quebra de linha
existe neles; reabrir é decisão à parte.

A recomendação da máquina (10 aprovar / 7 rejeitar) fica abaixo, como
histórico. Os 10 "aprovar" estavam forçados.

| # | item | sev/cat | problema (resumo) | veredito | por que |
|---|------|---------|-------------------|----------|---------|
| 1 | 1.1 | baixo/estrutural | não indica prazo de vigência | **rejeitar** | 1.4, 10.1 e 11.1 fixam 24 meses. Omissão que existe no TR não é achado do item. |
| 2 | 2.1.5 | baixo/estrutural | título incompleto ("todas as") | **rejeitar** | Frase fecha: "todas as atividades necessárias… durante a vigência contratual." |
| 3 | 3.1.4 | info/estrutural | título termina em "da" | **rejeitar** | "essencial da contratação" continua no mesmo item. Não é o TP humano ("abruptamente"). |
| 4 | 3.1.6 | baixo/estrutural | título truncado | **rejeitar** | Frase fecha em "princípios aplicáveis às contratações públicas." |
| 5 | 3.1.6 | info/estrutural | título termina em "à" | **rejeitar** | Duplicata do 4. "contínua à necessidade institucional" continua na linha seguinte. |
| 6 | 4.2.2 | baixo/estrutural | título termina em "a" | **rejeitar** | O "a" é quebra antes de "CONTRATADA deverá possuir autorização da ANATEL…". |
| 7 | 4.3 | alto/estrutural | título-só, sem conteúdo | **rejeitar** | Cabeçalho de seção, igual a 4.1, 4.2, 4.4. O requisito está em 4.3.1–4.3.5. Art. 6º XXIII c, d, g vale para o TR, não para o título. A checagem da máquina ("plataforma de PABX não aparece em outro trecho") é falsa: 4.3.1 e 2.1.3 b) trazem a plataforma. |
| 8 | 4.3.3 | baixo/estrutural | título truncado ("sem") | **rejeitar** | "sem limitação de chamadas entre os ramais…" fecha o item. |
| 9 | 4.5.3 | info/estrutural | título truncado ("de") | **rejeitar** | "de forma a reduzir os riscos de interrupção…" fecha o item. |
| 10 | 4.6.4 | baixo/estrutural | título termina em "por meio de" | **rejeitar** | "por meio de canais oficiais de atendimento…" fecha o item. |
| 11 | 4.9.1 | alto/estrutural | sem critério p/ medidas de segurança | **rejeitar** | 4.9.2–4.9.7 detalham LGPD, autenticação, acesso individual, sigilo, incidente e devolução. Art. 6º XXIII g é medição/pagamento e h é seleção do fornecedor — não é base para este achado. "Relatórios gerenciais" está em 2.1.3 i). |
| 12 | 4.9.2 | baixo/estrutural | sem subdivisões hierárquicas | **rejeitar** | Item único e completo (LGPD). Implicância. |
| 13 | 4.9.4 | info/estrutural | sem subdivisões hierárquicas | **rejeitar** | Idem 12. |
| 14 | a-2 | baixo/estrutural | numeração inconsistente | **rejeitar** | Alínea normal: "a) criação, alteração, exclusão e administração de ramais e usuários;". O id "a-2" é desambiguação do parser, não defeito do TR. |
| 15 | b-3 | baixo/estrutural | numeração inconsistente | **rejeitar** | Alínea normal: "b) disponibilização e configuração da plataforma de PABX em Nuvem;". |
| 16 | e | alto/jurídica | 200 DDR sem justificativa | **rejeitar** | 4.1.3 lista duas faixas de 100 números (3341-8000–8099 e 3341-8300–8399). 4.4.1 amarra os 200 DDR à portabilidade dessas faixas. Art. 23 é compatibilidade do valor estimado com o mercado e com as quantidades, não um vazio neste item. |
| 17 | k | baixo/estrutural | letra em vez de número + título | **rejeitar** | Alínea k de 2.1.3 está completa. Letra em lista é redação padrão. |

## Onde a máquina forçou

1. Classe T (2, 3, 4, 6, 8, 9, 10): precedente dos 3 TPs humanos tratado como mérito. O `content` parseado não está truncado.
2. Altos 7, 11 e 16: a "prova doc-wide" não confere com o PDF. 4.3 tem filhos; 4.9 tem critérios nos irmãos e a base legal citada não é a do achado; os 200 DDR são as duas faixas de portabilidade.
3. 14, 15 e 17: a revisão 2 já rejeitava. Mantido, com o texto da alínea.

## Histórico da recomendação da máquina (superada)

Revisão 2 pedia 10 aprovar (2, 3, 4, 6, 7, 8, 9, 10, 11, 16) e 7 rejeitar
(1, 5, 12, 13, 14, 15, 17). Este carimbo rejeita os 10.
