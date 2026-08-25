'use client';

import type { LucideIcon } from 'lucide-react';
import { Scale, Wrench, PenLine, Ruler } from 'lucide-react';

export const AGENT_ORIGIN_CONFIG: Record<string, { label: string; icon: LucideIcon; badgeClass: string }> = {
  juridico: { label: 'Agente Jurídico', icon: Scale, badgeClass: 'bg-purple-500/15 text-purple-300 border-purple-500/40' },
  tecnico: { label: 'Agente Técnico', icon: Wrench, badgeClass: 'bg-amber-500/15 text-amber-300 border-amber-500/40' },
  redacao: { label: 'Agente de Redação', icon: PenLine, badgeClass: 'bg-sky-500/15 text-sky-300 border-sky-500/40' },
  estrutural: { label: 'Agente Estrutural', icon: Ruler, badgeClass: 'bg-teal-500/15 text-teal-300 border-teal-500/40' },
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
