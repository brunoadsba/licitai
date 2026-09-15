# Guia do usuário — LicitAI

Para o elaborador de Termo de Referência (TR) na CODEBA.

Na aplicação: **Mais ferramentas → Guia do usuário** ou `/guia`.

**Regra:** só vai para o SEI o que você **aprovou** ou **ajustou**.

---

## Fluxo (4 passos)

1. **Enviar** o TR (PDF ou DOCX, até 50 MB)
2. **Aguardar** a análise (fila Prioridade: alto/crítico + Art. 6º primeiro)
3. **Revisar** — modo guiado 1 por vez ou "Ver todas"
4. **Copiar pacote SEI** e colar no processo

---

## Telas

### Painel
- Lista dos TRs e status (Pronto para análise, Concluído).
- **Enviar TR** — novo arquivo.
- Por linha: **Analisar**, **Ver resultado** ou **Acompanhar**.
- Se houver pendências: **Continuar revisão**.
- Widget **Revisor-assistente** mostra taxa de aceitação das sugestões (quando houver uso).

### Enviar TR
1. Arraste ou escolha o arquivo.
2. Clique em **Enviar e Analisar**.
3. Acompanhe o progresso na tela.

**Opções avançadas** (recolhidas): revisão completa, proposta, comparação de versões. Abra só se precisar.

### Análise — dois modos

**Revisar agora (guiado — recomendado):**
- Mostra **1 sugestão prioritária por vez**, grave primeiro.
- Topo: **"3 de 9"** + barra de progresso.
- Em cada sugestão: **Sugestão: aprovar 84% · motivo** + botão **Aceitar sugestão** (1 clique) ou **Aprovar / Rejeitar / Ajustar** manual.
- Se o texto tiver `[inserir]` ou `___`, o botão de aceitar fica desabilitado — use **Ajustar** e preencha.
- Ao aceitar/aprovar, a nota e o risco recalculam na hora.

**Ver todas:**
- Grid por item (lista à esquerda, detalhe à direita).
- Cada card mostra selo discreto **Sugestão: ...** quando pendente.
- Mesmo fluxo de Aprovar/Rejeitar/Ajustar; com pelo menos uma aprovada/ajustada: **Copiar pacote SEI**.
- **Exportar:** HTML, DOCX ou pacote `.md` (menu Exportar).
- **Mais:** relatório, histórico, reanalisar faltantes.
- **Perguntar:** dúvidas sobre o documento (copiloto).

### Painel Art. 6º
- Quanto do TR está completo nas 10 partes obrigatórias (meta sugerida ~90%).
- Itens faltantes aparecem como selos; confira antes de exportar.

### Relatório
- Resumo, pontuação (0-10), risco, parecer e **métrica do revisor** (aceitas/sobrepostas).
- **Exportar PDF** (impressão do navegador). O pacote SEI fica na Análise.

---

## Colar no SEI

1. Na Análise, **Copiar pacote SEI** (só habilita após aprovar/ajustar ao menos uma).
2. Cole na minuta/processo no SEI.
3. Confira o texto antes de concluir.

---

## Outros

| Item | Onde |
|------|------|
| Tema claro/escuro | Interruptor no cabeçalho |
| Gerar TR, Comparações, Versões, Moldes | Mais ferramentas (opcional) |
| 2ª opinião local | Env `REVIEWER_SECOND_OPINION=1` (Ollama local, opt-in) |

---

## Problemas comuns

| Situação | O que fazer |
|----------|-------------|
| Pacote SEI desabilitado | Aprove ou ajuste ao menos uma correção |
| Arquivo rejeitado | Use PDF ou DOCX, até 50 MB |
| Painel / Comparações / Moldes vazios | Normal no início: envie um TR no Painel |
| Sugestão com baixa confiança | Confira o motivo e a fundamentação antes de aceitar |
| Sistema indisponível | Avise o suporte / equipe do piloto |

---

*Acesso e ambiente: suporte CODEBA / equipe do piloto LicitAI.*
