'use client';

import type { AnalysisDetailResponse } from '@/types';
import type { Tone } from '@/components/ui/Badge';
import { Badge } from '@/components/ui/Badge';
import { Bot, Scale, Wrench, PenLine, Ruler } from 'lucide-react';

interface AnalysisProgressProps {
  analysis: AnalysisDetailResponse;
}

const AGENT_BADGES: { label: string; icon: typeof Scale; tone: Tone }[] = [
  { label: 'Jurídico', icon: Scale, tone: 'juridica' },
  { label: 'Técnico', icon: Wrench, tone: 'tecnica' },
  { label: 'Redação', icon: PenLine, tone: 'redacao' },
  { label: 'Estrutural', icon: Ruler, tone: 'estrutural' },
];

/**
 * Barra de progresso da análise em execução com shimmer e badges dos agentes ativos.
 */
export default function AnalysisProgress({ analysis }: AnalysisProgressProps) {
  const pct = Math.min(
    100,
    Math.round(((analysis.analyzed_items || 0) / (analysis.total_items || 1)) * 100),
  );

  return (
    <div role="status" className="glass-card space-y-3 border-accent-500/25 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center">
            <div className="absolute h-3 w-3 animate-ping rounded-full bg-accent-400 opacity-75" />
            <div className="h-3 w-3 rounded-full bg-accent-500" />
          </div>
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-content-primary">
              <Bot className="h-4 w-4 text-accent-400" aria-hidden />
              Análise em andamento
            </h3>
            <p className="text-xs text-content-muted">
              Revisando o TR sob os eixos jurídico, técnico, redacional e estrutural (Lei 14.133/21)
            </p>
          </div>
        </div>

        <div className="text-right">
          <span className="tnum block font-mono text-xl font-semibold text-accent-400">{pct}%</span>
          <span className="tnum block font-mono text-xs text-content-muted">
            {analysis.analyzed_items} de {analysis.total_items} itens processados
          </span>
        </div>
      </div>

      <div
        className="progress-bar"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="progress-bar-fill" style={{ width: `${Math.min(100, Math.max(4, pct))}%` }} />
      </div>

      <div className="flex items-center gap-2 overflow-x-auto pt-1">
        <span className="mr-1 shrink-0 text-[11px] font-medium text-content-muted">Agentes ativos:</span>
        {AGENT_BADGES.map((agent) => (
          <Badge key={agent.label} tone={agent.tone} className="animate-pulse text-[10px]">
            <agent.icon className="h-3 w-3" aria-hidden />
            {agent.label}
          </Badge>
        ))}
      </div>
    </div>
  );
}
