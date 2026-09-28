# Análise do plano UX-Confiança

Data: 28/09/2026
Documento analisado: [plano-ux-confianca-2026-09-28.md](../plano-ux-confianca-2026-09-28.md)
Contexto: [memory.md](../../memory.md), [recall-tr-real-2026-09.md](recall-tr-real-2026-09.md) e código do frontend/backend na mesma data.

Veredito: a direção está certa (honestidade na interface, sem backend e sem modelo novo), mas o plano ainda não está pronto para implementar. Três decisões de produto travam o 9,0. Quatro buracos já estão provados no código: o relatório não traz cobertura, o número de precisão não existe na fonte citada, a retomada por índice pula cartão, e o teclado ignora Ajustar.

Dois ajustes mecânicos já foram aplicados no plano: o aceite da página de confiança passou de 4 para 5 blocos; o grep da fase P2 passou a apontar `frontend/src`.

---

## 1. O que o plano acerta

O recorte combina com o piloto descrito no memory:

- Next 14.2 permanece (Next 15 fora de escopo, correto).
- Sigilo fail-closed, fila de negócio e API de `evidence` não são tocados.
- A fila 1-por-1, o banner de análise parcial e os textos do elaborador já existem.
- O ganho novo que importa é calibrar a nota, retomar a fila e não prometer adequação geral.

O princípio (“toda afirmação da UI sobre qualidade vem de número medido e linkado”) é o certo para um piloto assistido, não para confiança cega. O risco é o plano certificar 9,0 com uma página de números que o elaborador pode nunca abrir, enquanto o recall real continua 0,25 (3/12) e o carimbo humano do golden segue pendente.

---

## 2. Três decisões que travam o 9,0

Estas três precisam de resposta do Bruno antes de abrir `feat/ux-confianca`. Sem isso, cada implementador escolhe um 9,0 diferente.

### 2.1 Página `/confianca` versus limites no relatório

O P0 gasta rota nova, módulo estático, links de nav e spec Playwright para um catálogo que o elaborador pode ignorar. O critério 1 (“revisor novo entende os limites”) fecha se a rota renderiza, não se a incerteza aparece na tela em que ele já trabalha.

Opções:

1. Cortar a rota. Colocar os quatro limites + fonte no veredito do relatório (e, se preciso, uma seção em `/guia`).
2. Manter a rota como detalhe, mas o 9,0 só fecha com a faixa calibrada visível no relatório/análise.
3. Manter o P0 como está e aceitar que a nota mede a existência da página, não a honestidade do fluxo.

Recomendação: opção 2. `/guia` já é “Como usar”; não duplicar ajuda. Se a rota existir, ela é secundária. Header e rodapé do relatório apontam “Como confiamos”; a sidebar, se ganhar o link, coloca `/guia` primeiro.

### 2.2 Fazer agora versus carimbo e Go/No-Go

O gate de 14 dias fechou em 28/09. Pendências humanas no memory: carimbo do golden, anotar TR real, colar SEI, decidir Go/No-Go. O QA deste plano (“revisar 17 itens só com teclado”) compete com as mesmas horas.

Se o 9,0 de honestidade depende de número medido e linkado, publicar a página agora congela um harness (0,25) que o próprio doc de ops recusa chamar de recall.

Recomendação: não gastar QA desta branch em paralelo com a anotação dos 17 pendentes. Ou a branch espera o carimbo, ou o bloco Recall sai como “não carimbado” e o 9,0 não fecha.

### 2.3 9,0 no fim da branch versus 9,0 por fase

Os três critérios de pronto cobrem P0 + P1 + P2. P0 sozinho não entrega “revisa 17 itens sem se perder” nem “nenhuma tela promete adequação absoluta”. Merge só no fim amarra a nota a trabalho posterior; a fase “o que mais pesa na nota” não é entregável sozinha.

Recomendação: ou o 9,0 vira gate da branch inteira (e o P0 deixa de ser vendido como a nota), ou progresso/retomada sobe para P0 e a varredura P2 fica restrita a copy que afirma adequação.

---

## 3. Buracos que o código já prova

### 3.1 Relatório não tem cobertura de itens

O plano exemplifica “Nota 9,3 — na cobertura analisada (186/257 itens)” na página de relatório. `getReport` devolve `ReportResponse`: tem `status` e parecer, não tem `analyzed_items` nem `total_items`. Esses campos existem no detalhe da análise (`AnalysisDetailResponse`), usado na tela `/analysis/[id]`. O banner `completed_with_errors` também vive nessa tela, não no relatório.

Com “nenhuma mudança de backend”, o implementador ou inventa o N, ou chama o detalhe da análise além do relatório. O exemplo 9,3 + 186/257 ainda mistura dois jobs de referência (`8cdafd60` nota 9,3 concluído; `f9648727` parcial 186/257).

Correção concreta: na página de relatório, além de `getReport`, chamar o detalhe da análise já existente e ler cobertura e status de lá. Envolver o parecer bruto com o mesmo aviso de cobertura. Não reescrever o texto do backend. Sem isso, o aceite “relatório parcial nunca afirma adequação geral” falha: o bloco Parecer Final continua absoluto e o botão copia esse texto para o SEI.

### 3.2 Precisão sem número na fonte citada

A tabela da página de confiança aponta [recall-tr-real-2026-09.md](recall-tr-real-2026-09.md) como fonte de precisão. Esse doc não traz precisão. Traz recall 0,25 (3/12) nos dois runs e uma “Leitura honesta”: medir as análises que geraram os achados valida o harness, não o recall. A régua `test_analysis_precision` é outro objeto (precisão humana 0,09–0,18 em 11 casos). O memory ainda lista Groq P 1,0 e recall antigo 0,67 / 0,00.

Publicar qualquer um desses sem decisão no plano quebra a própria regra “nenhum número sem fonte linkada”.

Números a gravar, se a página (ou o rodapé do relatório) existir:

- Recall: 0,25 (3/12), aviso de que valida o harness, carimbo humano pendente. Fonte: o doc de ops. Proibido o 0,67/0,00 do memory.
- Precisão: “ainda não medido neste golden (carimbo humano pendente)”, mesmo doc. Não copiar P 1,0 do Groq.

Dono e gatilho: quem reescreve a fonte única, e em qual evento (nova medição no ops ou carimbo no golden). Sem isso, a página mente com um número “linkado” na primeira medição seguinte. Fonte canônica: o doc de ops vence o memory.

### 3.3 Retomada por índice pula cartão

`GuidedReview` já filtra só pendentes prioritários. Depois de aprovar, a lista encolhe; o mesmo índice passa a ser outro cartão. Gravar “último índice” e recarregar retoma o item errado. A barra atual é `i de total` de pendentes (encolhe); o plano pede “X de Y revisados” com Y estável (“total corrigível”), sem definir Y frente ao filtro de prioridade.

Correção concreta:

- Persistir o id da correção, não o índice.
- No load: se o id ainda estiver pendente, abrir esse card; senão o primeiro pendente.
- “X de Y” = revisados / correções prioritárias, independente da fila só-pendentes.
- Não criar terceiro filtro. Guiado continua só pendentes. “Ver todas” sai do guiado e não lê nem grava retomada.
- Bound: mesmo browser, piloto single-user. Não sobrevive outro perfil, host Windows vs WSL, nem modo privado.
- Não recriar a barra nem o default “só pendentes” — só a retomada é escopo novo.

### 3.4 Teclado ignora Ajustar

A revisão humana tem três ações: Aprovar, Rejeitar, Ajustar. Placeholder bloqueia aprovar e abre o campo de ajuste. Atalhos só `a` / `r` / `n` não cobrem Ajustar. O gate “17 itens só com teclado” trava nesses cards. Na mesma página há o campo do Copiloto e, ao ajustar, outro campo de texto.

O plano aponta o skip-link da página (“Pular para o conteúdo”) como foco após decidir. Esse link não é o card. `CorrectionCard` remonta com `key={current.id}`; o foco cai no `body`.

Correção concreta:

- `j` abre Ajustar e foca o campo.
- Ignorar atalhos se o foco estiver em campo de texto ou dentro de um dialog.
- Com placeholder, `a` não aprova: abre Ajustar.
- `n` nunca conta como decisão.
- Depois de decidir, focar o wrapper do próximo card. Estado vazio: focar “Ver todas”.
- `?` alterna um disclosure no rodapé (não modal). Em ponteiro grosso, não registrar atalhos; deixar Anterior/Próxima.

---

## 4. Demais achados (implementar depois das decisões)

### P1 — fechar no texto do plano

| Item | Efeito se ficar como está | Mudança |
|---|---|---|
| `claim_support` não está em `evidence` | Chip “2/2 afirmações” nasce vazio | Ler `grounded` e `legal_valid` de `evidence`; `claim_support` no topo da correção. Sem `evidence`, ainda renderizar os três chips. |
| “17 itens” sem referente | QA certifica o golden de anotação, não a fila viva | Os 17 são cards da fila guiada de uma análise nomeada, não a planilha `anotacao_pabx_pendentes.md`. |
| P0.2 lista só a página de relatório | Banner “faltam N itens” não entra no escopo | Incluir o banner da análise e a rota `/analysis/[id]` na lista de arquivos. |
| `CalibratedVerdict` novo | Arquivo extra para a frase que já vive em `ReportScores` | Calibrar dentro de `ReportScores`; não criar componente novo só por texto. |
| Varredura P2 sem bound | `copy.ts` estoura 200 linhas e vira higiene de jargão | Limitar a copy que afirma adequação/completude no relatório e nos banners. Não varrer toda lista vazia nem nomes de env. |
| Gates de saída inchados | `up.sh --build` + smoke + BFF não provam transparência | Gates: `tsc`, Vitest, Playwright da faixa calibrada e do teclado (mock). QA de 17 itens só depois do P1 de teclado. |
| Ajuda `?` e foco | Playwright e o rodapé divergem; o primeiro Aprovar perde o teclado | Ver seção 3.4. |
| Parecer copiado ao SEI | Honestidade na tela, minuta absoluta | Residual aceito, ou aviso na ação de copiar. O critério de honestidade precisa dizer se cobre o parecer. |

### P2 — registrar, não bloquear

- Três chips sempre visíveis: verdadeiro / falso / ausente. `legal_valid` já pode ser nulo; `grounded === false` já tem “trecho não ancorado”.
- `/confianca` e `/guia` não são a mesma página. Se as duas existirem, papéis distintos.
- Critério 1 é falsificável só se o usuário abrir a página — ou os limites aparecem no relatório.

---

## 5. Caminho mínimo (se a decisão for implementar)

1. Calibrar nota e parecer na página de relatório, buscando cobertura no detalhe da análise já existente.
2. Publicar recall 0,25 (3/12) como validação de harness, com carimbo pendente. Não copiar 0,67 nem precisão 1,0.
3. Gravar o id da correção, não o índice. Incluir Ajustar no teclado. Não recriar barra nem filtro.
4. Não fechar o 9,0 só porque a rota de confiança renderiza.
5. Não paralelizar QA desta branch com a anotação dos 17 pendentes do golden.

Fora deste recorte: reescrever score/parecer no backend, Next 15, multiusuário, mudar `evidence` da API.

---

## 6. Método da revisão

Revisores: coerência, viabilidade, produto, design, escopo, adversarial.
Segurança não ativada (sem auth, PII ou pagamento).
Passe entre modelos pulada: família do host nesta sessão não atestada; não há corroboração independente entre modelos.

Contagem pós-síntese: 2 ajustes mecânicos aplicados no plano; 24 itens em aberto (propostas concretas + decisões); 2 observações de produto rebaixadas (P0 atende a nota, não o elaborador; página avulsa é incremento evitável).

Observações que não viraram achado, mas o implementador deve saber:

- Copiloto na análise (dialog) compete com os atalhos globais.
- Publicar 0,25 visível pode fazer o elaborador parar de rodar análise em vez de revisar assistido.
- Depois de Aprovar, Anterior deve reabrir o card já revisado ou só os pendentes restantes? O plano não diz.
- `n` extra, se a fila já avança sozinha, pula um item.
