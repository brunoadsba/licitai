# Anotação PABX — 17 pendentes (pré-preenchido pela máquina, 28/09/2026)

## Contexto para o revisor externo (leia primeiro)

- **O que é isto:** fila de anotação humana do TR `09-ti-pabx-nuvem` (PABX em nuvem, CODEBA). Cada linha é um achado gerado por IA multiagente que um humano ainda não julgou. Seu veredito vira verdade de medição (golden): aprovado = problema real; rejeitado = falso positivo conhecido.
- **Regra de ouro: precisão > recall.** Em dúvida, REJEITE. Um falso positivo no SEI custa mais que um miss.
- **Legenda de grupo (agrupamento, NÃO veredito):** `T` = título truncado/incompleto, mesmo defeito dos 3 já aprovados (3.1.1/3.1.2/3.1.4) · `N` = caso novo, exige olho jurídico · `R` = classe de ruído já rejeitado.
- **Doutrina do projeto:** checklist do Art. 6º XXIII vale para o TR inteiro, não para a cláusula isolada — omissão que existe em outro trecho do documento NÃO vira achado do item.
- **Histórico desta planilha:** revisão 1 da máquina (14 aprovar) → crítica externa apontou T esticado, 1.1 sem conferência e duplicata 4/5 → revisão 2 com prova nos dados (TR contém "contrato será de 24 meses"; 4 e 5 têm mesmo trecho e mesma sugestão). Placar atual: **10 aprovar, 7 rejeitar, 0 condicionais**.
- **O que pedimos de você:** veredito independente por item + apontar onde a recomendação da máquina ainda está forçada. Desconfie especialmente de achados sem base legal e de severidade baixa.


**Como usar:** para cada linha, marque UM veredito e devolva. A coluna
"padrão" só agrupa por semelhança com os 3 já aprovados — **não é veredito**,
não confie nela. Em dúvida, rejeite (precisão > recall nesta fase).

Legenda padrão: `T` = mesmo padrão dos títulos truncados aprovados (3.1.1/3.1.2/3.1.4) · `N` = caso novo, exige olho jurídico · `R` = mesma classe de ruído já rejeitado (4.9.2).

| # | item | sev/cat | problema (resumo) | base legal? | padrão | veredito [ ] | obs |
|---|------|---------|-------------------|-------------|--------|--------------|-----|
| 1 | 1.1 | baixo/estrutural | não indica prazo de vigência | não | N | [ ] aprovar [ ] rejeitar | omissão — conferir no TR inteiro antes |
| 2 | 2.1.5 | baixo/estrutural | título incompleto ("todas as") | não | T | [ ] aprovar [ ] rejeitar | |
| 3 | 3.1.4 | info/estrutural | título termina em "da" | não | T | [ ] aprovar [ ] rejeitar | |
| 4 | 3.1.6 | baixo/estrutural | título truncado | não | T | [ ] aprovar [ ] rejeitar | |
| 5 | 3.1.6 | info/estrutural | título termina em "à" | não | T | [ ] aprovar [ ] rejeitar | duplicado do 4? ver se é o mesmo defeito |
| 6 | 4.2.2 | baixo/estrutural | título termina em "a" | não | T | [ ] aprovar [ ] rejeitar | |
| 7 | 4.3 | **alto**/estrutural | título-só, sem conteúdo | sim (Art. 6º XXIII c,d,g) | N | [ ] aprovar [ ] rejeitar | alto fora do score até você decidir |
| 8 | 4.3.3 | baixo/estrutural | título truncado ("sem") | não | T | [ ] aprovar [ ] rejeitar | |
| 9 | 4.5.3 | info/estrutural | título truncado ("de") | não | T | [ ] aprovar [ ] rejeitar | |
| 10 | 4.6.4 | baixo/estrutural | título termina em "por meio de" | não | T | [ ] aprovar [ ] rejeitar | |
| 11 | 4.9.1 | **alto**/estrutural | sem critério p/ medidas de segurança | sim (Art. 6º XXIII g,h) | N | [ ] aprovar [ ] rejeitar | alto fora do score até você decidir |
| 12 | 4.9.2 | baixo/estrutural | sem subdivisões hierárquicas | sim (Art. 92 III) | R | [ ] aprovar [ ] rejeitar | classe do nitpick; se for implicância, rejeite |
| 13 | 4.9.4 | info/estrutural | sem subdivisões hierárquicas | sim (Art. 92 XVIII) | R | [ ] aprovar [ ] rejeitar | idem acima |
| 14 | a-2 | baixo/estrutural | numeração inconsistente | não | T | [ ] aprovar [ ] rejeitar | |
| 15 | b-3 | baixo/estrutural | numeração inconsistente | não | T | [ ] aprovar [ ] rejeitar | |
| 16 | e | **alto**/jurídica | 200 DDR sem justificativa | sim (Art. 23 + TCU) | N | [ ] aprovar [ ] rejeitar | **o mais importante** — decide o recall jurídico |
| 17 | k | baixo/estrutural | letra em vez de número + título | não | T | [ ] aprovar [ ] rejeitar | |

Regra de ouro: aprovou os 3 altos (7, 11, 16)? Eles entram no score e no SEI.
Rejeitou? Vira FP conhecido e alimenta o tripwire.

## Verificação doc-wide pedida na 2ª crítica (28/09, com prova)

- **4.3 (nº 7):** "requisitos da plataforma"/"plataforma de pabx" NÃO aparece em
  nenhum outro trecho do TR → lacuna real no documento. Aprovação sem ressalva.
- **4.9.1 (nº 11):** "auditoria"/"medidas de segurança"/"relatórios gerenciais"
  NÃO aparecem no TR → ausência de critério real. Aprovação sem ressalva.
- **DDR (nº 16):** só menção genérica; justificativa dos 200 ausente. Mantido.
- **Classe T:** a crítica procede em doutrina (precedente != mérito). Decisão
  proposta: manter por consistência com os 3 aprovados humanos; reabrir a
  classe exige julgamento humano, não desta máquina. Variante estrita
  documentada: 4 A / 13 R (só 4, 7, 11, 16).

## Recomendação técnica da máquina (28/09 — veredito continua seu)

Base: todos os 17 com `grounded=true` e `claim_support` cheio; todos passaram
nos gates. Critério: mesmo defeito dos 3 aprovados → aprovar; classe de ruído
já rejeitado → rejeitar; caso novo com evidência → aprovar c/ destaque.

| # | item | recomendação | motivo (1 linha) |
|---|------|--------------|------------------|
| 1 | 1.1 | REJEITAR (era aprovar) | prazo EXISTE no TR ("contrato será de 24 meses") — omissão desmentida |
| 2 | 2.1.5 | aprovar | mesmo padrão dos títulos truncados aprovados |
| 3 | 3.1.4 | aprovar | idem |
| 4 | 3.1.6 | aprovar | idem; ver duplicidade com o 5 |
| 5 | 3.1.6 | REJEITAR | duplicata confirmada: mesmo original_text e mesma sugestão do 4; fica o 4 (sev maior) |
| 6 | 4.2.2 | aprovar | idem padrão T |
| 7 | 4.3 | **aprovar** | item só-título sem conteúdo é lacuna real; base Art. 6º válida |
| 8 | 4.3.3 | aprovar | idem padrão T |
| 9 | 4.5.3 | aprovar | idem padrão T |
| 10 | 4.6.4 | aprovar | idem padrão T |
| 11 | 4.9.1 | **aprovar** | sem critério de avaliação de segurança é lacuna real; base Art. 6º válida |
| 12 | 4.9.2 | rejeitar | implicância cosmética (mesma classe do FP 4.9.2 já rejeitado) — mantido |
| 13 | 4.9.4 | rejeitar | idem |
| 14 | a-2 | REJEITAR (era aprovar) | T era só p/ títulos truncados; numeração sem base é cosmético |
| 15 | b-3 | REJEITAR (era aprovar) | idem 14 |
| 16 | e | **aprovar** | 200 DDR sem justificativa, trecho exato, base Art. 23 + TCU; maior valor do lote |
| 17 | k | REJEITAR (era aprovar) | idem 14 |

Revisão 2 (pós-crítica externa, com prova nos dados): **10 aprovar**
(2,3,4,6,7,8,9,10,11,16), **7 rejeitar** (1,5,12,13,14,15,17), 0 condicionais.
Mudanças vs revisão 1: 1→R (prazo existe), 5→R (duplicata provada),
14/15/17→R (T esticado além da definição).
Achado lateral: G4 deixou passar a omissão do 1.1 mesmo com "24 meses" no TR —
ponto de tuning futuro do gate, fora desta anotação.
