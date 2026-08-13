'use client';

export const AGENT_ORIGIN_CONFIG: Record<string, { label: string; icon: string; badgeClass: string }> = {
  juridico: { label: 'Agente Jurídico', icon: '⚖️', badgeClass: 'bg-purple-500/15 text-purple-300 border-purple-500/40' },
  tecnico: { label: 'Agente Técnico', icon: '🛠️', badgeClass: 'bg-amber-500/15 text-amber-300 border-amber-500/40' },
  redacao: { label: 'Agente de Redação', icon: '✍️', badgeClass: 'bg-blue-500/15 text-blue-300 border-blue-500/40' },
  estrutural: { label: 'Agente Estrutural', icon: '📐', badgeClass: 'bg-teal-500/15 text-teal-300 border-teal-500/40' },
};

export function getCategoryBadge(category: string) {
  const classes: Record<string, string> = {
    juridica: 'badge-juridica',
    tecnica: 'badge-tecnica',
    redacao: 'badge-redacao',
    estrutural: 'badge-estrutural',
  };
  return classes[category] || 'badge-info';
}

export function getSeverityBadge(severity: string) {
  const classes: Record<string, string> = {
    info: 'badge-info',
    baixo: 'badge-baixo',
    medio: 'badge-medio',
    alto: 'badge-alto',
    critico: 'badge-critico',
  };
  return classes[severity] || 'badge-info';
}
