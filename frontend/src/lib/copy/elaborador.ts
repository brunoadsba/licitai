/**
 * Microcopy leiga do caminho elaborador (Upload → Análise → SEI).
 * Títulos amigáveis primeiro; referência legal só quando necessário.
 */

export const ART6_PLAIN_LABELS: Record<string, string> = {
  objeto: 'O quê contratar',
  fundamentacao: 'Por que contratar',
  descricao_solucao: 'Solução completa',
  requisitos: 'Requisitos',
  modelo_execucao: 'Como executar',
  modelo_gestao: 'Como fiscalizar',
  criterios_medicao_pagamento: 'Medição e pagamento',
  selecao_fornecedor: 'Como escolher o fornecedor',
  estimativa_valor: 'Estimativa de preço',
  adequacao_orcamentaria: 'Verba / orçamento',
};

export function art6PlainLabel(key: string, fallback?: string): string {
  return ART6_PLAIN_LABELS[key] ?? fallback ?? key;
}

export function art6BadgeLabel(alinea: string, key: string, fallbackLabel?: string): string {
  return `${alinea}) ${art6PlainLabel(key, fallbackLabel)}`;
}

export function art6PanelTitle(pct: number): string {
  return `Partes obrigatórias do TR — ${pct}% completo`;
}

export function art6PanelSubtitle(gapCount: number): string {
  if (gapCount === 0) {
    return 'As 10 partes mínimas da lei parecem presentes.';
  }
  const n = gapCount === 1 ? '1 parte importante' : `${gapCount} partes importantes`;
  return `Faltam ${n}. Elas aparecem em “Revisar agora”.`;
}

export const ART6_TOOLTIP_INTRO =
  'A lei pede 10 partes mínimas no Termo de Referência (Art. 6º). Meta sugerida: cerca de 90% completo. Confira no texto antes de colar no SEI.';

export function art6TooltipBody(
  items: { key: string; alinea: string; label?: string }[],
): string {
  if (!items.length) return ART6_TOOLTIP_INTRO;
  const list = items
    .map((i) => `${i.alinea}) ${art6PlainLabel(i.key, i.label)}`)
    .join(' · ');
  return `${ART6_TOOLTIP_INTRO} Itens: ${list}`;
}

export const PRIORITY_QUEUE_HINT = 'Sugestões graves e partes faltantes do TR';

export const PRIORITY_SECTION_TITLE = 'Prioridade (graves + estrutura do TR)';

export const ANALYSIS_PARTIAL_TITLE = 'Análise concluída, mas alguns trechos falharam';

export const UPLOAD_STAGE_ANALYZING =
  'Analisando partes obrigatórias do TR e riscos jurídicos…';

export const ANALYSIS_MODE_ESSENTIAL = 'Revisão essencial';
export const ANALYSIS_MODE_FULL = 'Revisão completa';
export const ANALYSIS_MODE_HINT =
  'Essencial = estrutura do TR + riscos jurídicos. Completa = também técnico e redação.';

export const PROGRESS_ART6_LABEL = 'Estrutura do TR';

export const CATEGORY_PLAIN: Record<string, string> = {
  juridica: 'Jurídica',
  tecnica: 'Técnica',
  redacao: 'Redação',
  estrutural: 'Estrutura do TR',
};
