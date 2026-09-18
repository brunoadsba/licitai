# Plano — Análise realmente confiável (16/09/2026)

> Origem: crítica da análise `afd39876…` (TR 09-ti-pabx-nuvem) — 11 achados, precisão
> 9–18% pelo julgamento humano (9 rejeitadas, 1 aprovada, 1 ajustada). 6 classes de
> falha catalogadas. Proposta do Bruno (analisador + supervisor + coordenador) avaliada
> abaixo: **espírito aproveitado, implementação redirecionada** (ver §1).

## 1. Veredito sobre a ideia dos 3 agentes LLM

**Não implementar o "supervisor" como um segundo LLM relendo o mesmo texto.** Três motivos:

1. **Falhas correlacionadas.** Um LLM verifica mal o mesmo tipo de saída que outro LLM
   produziu — ambos "acham" que o trecho do RAG é do item ([0]), que 14.133 se aplica
   ([2]/[4]/[7]/[10]) e que a cláusula isolada basta ([10]). Evidência interna: o
   `review.py` (revisão cruzada) **já é** um supervisor e não barrou nenhum desses.
2. **Custo/latência dobram sem garantia.** A análise ouro consumiu ~237k tokens em
   ~8–13 min. Re-verificar tudo com LLM cheio vai a ~500k tokens e 15–25 min por TR —
   inviável no free tier (429 já é gargalo) e sem prova de ganho.
3. **As falhas são mecânicas, não de "raciocínio".** Trecho que não está no item,
   número que não está no documento, lei fora do regime, omissão desmentida por busca
   no próprio doc — tudo isso se verifica com código determinístico, grátis e 100%
   reproduzível.

**O que se aproveita da ideia:** a separação propor × verificar × alinhar, mas com o
"supervisor" implementado como **gate de evidências determinístico** + um **juiz LLM
somente para os casos ambíguos que sobreviverem ao gate**, recebendo o bloco completo
de contexto (nunca a cláusula isolada). O "coordenador" continua sendo o orquestrador
determinístico (merge/dedup/calibragem), não um terceiro LLM.

## 2. Meta e régua

- **Meta:** precisão dos achados ≥ 0.80 no golden set, zero sugestões com placeholders
  ou números inventados, `risk_level` recalibrado após revisão humana.
- **Baseline de hoje:** precisão 0.09–0.18 na análise `afd39876…` (1 aprovada + 1 parcial
  em 11). Qualquer fase que não mova essa régua foi esforço perdido.

## 3. Fases

### Fase 0 — Régua de regressão (primeiro, sem ela nada é mensurável)

- Congelar os 11 achados de `afd39876…` como casos rotulados (TP/FP + classe de falha)
  em `backend/tests/test_analysis_precision.py` (fixtures inline: item real + achado +
  veredito esperado).
- O teste deve **falhar com o gate desligado** e passar com ele ligado (prova que cada
  fase morde um FP conhecido).
- **Aceite:** suite verde; cada novo FP futuro vira caso rotulado antes do fix.

### Fase 1 — Gate de evidências determinístico (o "supervisor" que funciona)

Novo `backend/app/services/analyzer/evidence_gate.py`, aplicado entre engine e
persistência. Achado reprovado é **descartado com motivo logado** (auditoria), nunca
persistido como Correction:

- **G1 — trecho existe?** `original_text` com fuzzy-match (SequenceMatcher ≥ 0.8
  normalizado) no item citado. Mata a classe [0] (trecho do RAG passado por texto do item).
- **G2 — sugestão honesta?** `suggested_text` sem placeholders (regex `X/Y/Z`, `[…]`,
  "a definir", "N meses") e sem números/percentuais ausentes no original + documento.
  Mata [4] (30%/15%/20% inventados) e os placeholders de [10].
- **G3 — lei do regime?** `legal_basis` restrito à allowlist do regime detectado
  (§ Fase 2). Citação fora do regime → descartada, não "rejeitável depois". Mata a
  família [2]/[4]/[7]/[10].
- **G4 — omissão real?** Alegação de "não especifica X" exige **busca doc-wide**
  (FTS + embeddings) por X antes de aceitar. No caso 1.1, a busca encontra 1.4
  (24 meses), 4.3.2 (130 ramais) e 11.5 (prorrogação) → achado descartado ou convertido
  em "verificado: presente em 1.4/4.3.2/11.5".
- **Aceite:** os 6 FPs conhecidos barrados; custo LLM adicional **zero**; recall do
  golden sem queda (monitorar — ver Riscos).

### Fase 2 — Contexto cruzado (cura a "cegueira")

- **Detecção de regime:** sinais no documento (RILC, "estatal", "13.303" vs "14.133",
  órgão) → `regime ∈ {13.303, 14.133}` no snapshot; trava `legal_basis` e ajusta prompts.
- **Bloco em vez de cláusula:** agente estrutural recebe o grupo (ex.: seção 1.x inteira)
  ao julgar completude tipo alínea (a); checklist Art. 6º avaliado no nível
  bloco/documento, nunca na cláusula isolada.
- **Anti-truncamento:** garantia de fatia íntegra (overlap + validação de fronteira) —
  mata a classe [6]/[9] (defeito que era artefato de segmentação).
- **Aceite:** re-run do 09-ti-pabx-nuvem não reemite [10]; nenhum achado cita trecho truncado.

### Fase 3 — Juiz com contexto + fim do ruído operacional

- **Juiz LLM só no ambíguo:** apenas achados aprovados no gate e marcados como
  ambíguos vão ao juiz, com bloco completo + trechos recuperados. Casos determinísticos
  (G1–G4 reprovados) nem chegam ao LLM — **o gate reduz chamadas, compensando o juiz**.
- **Falha de cobertura ≠ achado:** "Reexecutar a análise" ([1]/[3]/[5]/[8]) vira banner
  operacional + lista de itens não cobertos; nunca `Correction` com severity; excluído
  de score e risco. Exigir `legal_basis` + alteração textual para persistir qualquer
  Correction (regra dura no schema).
- **Aceite:** zero corrections sem fundamento/alteração textual; risk/score calculados
  só sobre achados reais.

### Fase 4 — Recalibragem e métricas visíveis

- **Teste dirigido do `risk_level`:** GET da análise antes/depois de rejeição em massa
  (caso real: 9/11 rejeitadas e risco seguiu `alto`). Confirmar/fixar
  `recalculate_analysis_scores` no PATCH de review.
- **Precision por análise** (aprovadas+ajustadas / total) no relatório/dashboard,
  estendendo o `review_suggestion_*` existente para corrections.
- **Guia de revisão:** orientar a nota com o motivo raiz (ex.: em [10], "informação
  existe em 1.4/4.3.2/11.5" em vez de só "lei fora do contexto") — alimenta o dataset
  que um dia destrava fine-tune.
- **Aceite:** risco cai após rejeições; precision visível por análise no dashboard.

## 4. Riscos e antídotos

| Risco | Antídoto |
|---|---|
| Gate agressivo derruba recall (some achado real junto) | G4 converte em "verificado" em vez de descartar quando a evidência é parcial; recall medido no golden a cada fase |
| Juiz com bloco maior estoura `ANALYSIS_MAX_LLM_CALLS`/cota | Gate elimina ~1/3 de ruído antes (as 4 operacionais); juiz só no ambíguo — saldo esperado neutro ou negativo em tokens |
| Regime detectado errado trava lei correta | Regime entra no snapshot e é exibido na UI; fallback: allowlist união + aviso quando ambíguo |

## 5. Fora de escopo (não fazer agora)

LangGraph, fine-tune/ML supervisionado, multi-tenant/RBAC, K8s — consistente com o
memory. Dataset para futuro ML nasce na Fase 4 (reviews com motivo raiz).

## 6. Ordem de execução

Fase 0 → Fase 1 (maior ganho por custo quase zero) → Fase 3-parte operacional
(1 linha de separação, ganho imediato de precisão aparente) → Fase 2 → Fase 3-juiz →
Fase 4. Cada fase entrega sozinha e é validada pela régua antes da próxima.
