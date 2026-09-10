'use client';

import type { LucideIcon } from 'lucide-react';
import { Scale, Wrench, PenLine, Ruler } from 'lucide-react';
import type { Tone } from '@/components/ui/Badge';

export type { Tone };

export const AGENT_ORIGIN_CONFIG: Record<
  string,
  { label: string; icon: LucideIcon; tone: Tone }
> = {
  juridico: { label: 'Agente Jurídico', icon: Scale, tone: 'juridica' },
  tecnico: { label: 'Agente Técnico', icon: Wrench, tone: 'tecnica' },
  redacao: { label: 'Agente de Redação', icon: PenLine, tone: 'redacao' },
  estrutural: { label: 'Agente Estrutural', icon: Ruler, tone: 'estrutural' },
};

export function getCategoryTone(category: string): Tone {
  const tones: Record<string, Tone> = {
    juridica: 'juridica',
    tecnica: 'tecnica',
    redacao: 'redacao',
    estrutural: 'estrutural',
  };
  return tones[category] ?? 'neutral';
}

export function getSeverityTone(severity: string): Tone {
  const tones: Record<string, Tone> = {
    info: 'info',
    baixo: 'low',
    medio: 'medium',
    alto: 'high',
    critico: 'critical',
  };
  return tones[severity] ?? 'neutral';
}

/** @deprecated Use getCategoryTone */
export const getCategoryBadge = getCategoryTone;
/** @deprecated Use getSeverityTone */
export const getSeverityBadge = getSeverityTone;
