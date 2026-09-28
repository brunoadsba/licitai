## Análise do Plano UX-Confiança

O plano é **bom, maduro e bem delimitado**. Ataca o ponto certo (honestidade + cansaço do revisor), tem escopo explícito, aceites por fase e critério de 9,0 definido. Ainda assim, há lacunas que podem fazer o plano **não entregar o 9,0** ou **criar novas dívidas**. Segue diagnóstico e ajustes.

---

### 1. O que está bem

- **P0 ataca o que mais pesa**: página `/confianca` com números linkados e relatório calibrado. A regra “nenhum número sem fonte” é excelente.
- **Separação clara de camadas**: calibragem é apresentação, não reescreve `final_opinion`. Evita retrabalho de backend.
- **P1 resolve dor real**: progresso + retomada + evidência + teclado atacam diretamente o “revisar 17 itens sem se perder”.
- **P2 com varredura automatizável**: grep + `copy.ts` + aceite objetivo.
- **Fora de escopo explícito**: evita scope creep.
- **Gates de saída por fase**: `tsc`, Vitest, Playwright, `next build`. Bom.

---

### 2. Lacunas e riscos por fase

#### P0.1 — Página `/confianca`

| Risco | Detalhe | Ajuste |
|---|---|---|
| **Números obsoletos** | “atualizada a cada medição” é manual. Nada impede a página ficar meses desatualizada. | Adicionar **gate de staleness**: se `last_updated > 30 dias`, build/teste falha ou mostra banner “números desatualizados”. |
| **Dados ausentes** | O que renderiza se um número ainda não foi medido (ex.: recall “em validação”)? | Definir **fallback explícito** por bloco: “ainda não medido” + link para o doc, nunca zero. |
| **Texto de limites sem dono** | “texto fixo revisado” — por quem? | Nomear revisor (jurídico/humano) e versionar o texto em `copy.ts` com data. |
| **Rota sem backend** | Bom, mas o `confidence.ts` precisa de **schema** para não virar string solta. | Definir tipo `ConfidenceBlock` com `value`, `source`, `lastUpdated`, `status`. |

#### P0.2 — Relatório calibrado

| Risco | Detalhe | Ajuste |
|---|---|---|
| **Limiar de calibragem indefinido** | Quando a ressalva aparece? Cobertura < 100%? < 80%? | Definir **threshold explícito** (ex.: cobertura < 95% → faixa + ressalva; 100% → nota direta). |
| **Score enganoso com cobertura baixa** | “Nota 9,3 — na cobertura analisada (186/257)” ainda pode ser lido como 9,3 geral. | Se cobertura < X, mostrar **faixa** (“entre 6 e 9,3”) ou **ocultar score** e mostrar só “análise parcial”. |
| **Print/screenshot sem contexto** | Usuário compartilha o número sem a ressalva. | Ressalva **inline e visualmente colada** ao número (não só link). Considerar marca d’água no print. |
| **`CalibratedVerdict.tsx` ~60 linhas** | Ok, mas precisa de **teste unitário** (Vitest) para os 3 estados: completo, parcial, erro. | Adicionar teste ao aceite. |

#### P1.1 — Progresso e retomada

| Risco | Detalhe | Ajuste |
|---|---|---|
| **“corrigível” indefinido** | “review_status != pendente / total corrigível” — o que é corrigível? | Definir: itens com `sev ∈ {alto, crítico}` ou todos? Explicitar na UI (“X de Y itens revisáveis”). |
| **localStorage frágil** | Análise re-rodada muda IDs; storage limpo perde posição; múltiplas abas. | Fallback gracioso + botão “recomeçar do topo”. Testar com storage vazio e corrompido. |
| **Filtro “só pendentes” default** | Pode esconder itens já aprovados que o revisor quer reconferir. | Já previsto “ver-todas”. Adicionar **contador** no filtro (“3 pendentes”). |

#### P1.2 — Evidência visível

| Risco | Detalhe | Ajuste |
|---|---|---|
| **Nomes internos viram UI** | `grounded`, `legal_valid`, `claim_support` são jargão. | Mapear em `copy.ts`: “trecho confirmado no TR”, “base legal válida”, “2/2 afirmações verificadas”. |
| **API pode não expor tudo** | O plano afirma “a API já entrega”. **Verificar antes de começar.** | Se `legal_valid` ou `claim_support` não vierem, isso **contradiz** “nenhuma mudança de backend”. Checar contrato. |
| **“sem evidência registrada”** | Pode ser lido como “correção ruim”. | Microcopy neutra: “evidência não registrada nesta análise” + link “por quê?”. |

#### P1.3 — Teclado

| Risco | Detalhe | Ajuste |
|---|---|---|
| **Sem undo** | `a`/`r` acidental é irreversível. Crítico em fluxo rápido. | Adicionar **undo** (Ctrl+Z ou toast “desfazer” por 5s). |
| **Conflito com modais** | Atalho dispara com modal/chat aberto. | Guardar `document.activeElement` + estado de modal. Testar com `ChatInput` focado. |
| **Modificadores** | `Ctrl+A`, `Cmd+R` etc. | Ignorar quando `ctrlKey/metaKey/altKey` pressionados. |
| **Acessibilidade** | Atalhos não descobertos por leitor de tela. | `aria-keyshortcuts` + ajuda `?` acessível. |
| **Auto-avanço** | Após decidir, avança? Foco vai ao próximo? | Definir comportamento e testar. |

#### P2 — Microcopy

| Risco | Detalhe | Ajuste |
|---|---|---|
| **Comando `rg` errado** | `rg --include='*.tsx'` não existe; ripgrep usa `-g`. | Corrigir para `rg -g '*.tsx' -g '*.ts'`. Incluir `.ts` além de `.tsx`. |
| **Erros da API não cobertos** | Mensagens do backend podem vazar jargão. | Incluir **mapeamento de erros** no inventário. |
| **Strings em `copy.ts`** | O próprio `copy.ts` pode ter jargão. | Incluir no grep. |
| **Datas/números** | Formato `en-US` vs `pt-BR`. | Padronizar locale no inventário. |

#### Gates

| Risco | Detalhe | Ajuste |
|---|---|---|
| **Sem gate de acessibilidade** | Atalhos, chips, contraste. | Adicionar `@axe-core/playwright` ou `pa11y` no CI local. |
| **Sem métrica de sucesso** | Como saber se chegou a 9,0? | Medir **tempo de revisão** e **taxa de undo** antes/depois (lightweight, sem telemetria invasiva). |
| **QA manual com 17 itens** | Amostra pequena. | Usar um TR maior (ex.: `f9648727` com 257 itens) para testar progresso/retomada. |

#### Critério de 9,0

- Subjetivo (“revisor novo entende”). **Sugestão**: transformar em **teste de usabilidade curto** (1 revisor não-técnico, 3 tarefas, sucesso sim/não). Sem isso, o critério vira opinião.

---

### 3. Melhorias adicionais (não previstas)

1. **Undo global** na fila guiada (P1.3) — o item mais crítico que falta.
2. **Gate de staleness** em `/confianca` (P0.1) — evita a página virar mentira.
3. **Threshold explícito** de calibragem (P0.2) — sem isso, a “faixa” é arbitrária.
4. **Verificar contrato da API** antes de prometer “sem backend” (P1.2).
5. **A11y gate** nos gates de saída.
6. **Métrica de sucesso** (tempo de revisão, undo) para validar 9,0.
7. **Print-friendly** do relatório com ressalva embutida.
8. **Empty state** de `/confianca` quando não há medição.
9. **Teste unitário** do `CalibratedVerdict`.
10. **`aria-live`** para feedback de aprovar/rejeitar (leitores de tela).

---

### 4. Veredito

O plano está **aprovado com ajustes**. Sem os ajustes, ele entrega ~8,5–8,7, não 9,0. Os pontos que mais pesam:

- **P0**: falta gate de staleness + threshold de calibragem + fallback de dados ausentes.
- **P1**: falta undo no teclado + definição de “corrigível” + verificação do contrato da API.
- **P2**: comando `rg` errado + mapeamento de erros da API.
- **Gates**: falta a11y + métrica de sucesso.

Com esses ajustes, o plano fica **coerente com a doutrina do projeto** (precisão > recall, nada absoluto, tudo medido e linkado) e atinge o objetivo sem criar dívida nova.