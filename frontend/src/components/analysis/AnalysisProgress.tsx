'use client';

import type { AnalysisDetailResponse } from '@/types';
import { FileSearch, Scale, Ruler, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AnalysisProgressProps {
  analysis: AnalysisDetailResponse;
}

const STAGES = [
  { id: 'parse', label: 'Lendo PDF', icon: FileSearch, minPct: 0 },
  { id: 'art6', label: 'Estrutura do TR', icon: Ruler, minPct: 15 },
  { id: 'legal', label: 'Riscos jurídicos', icon: Scale, minPct: 40 },
  { id: 'done', label: 'Pronto', icon: CheckCircle2, minPct: 100 },
] as const;

/**
 * Progresso da análise por estágios claros (sem jargão de “quatro agentes”).
 */
export default function AnalysisProgress({ analysis }: AnalysisProgressProps) {
  const pct = Math.min(
    100,
    Math.round(((analysis.analyzed_items || 0) / (analysis.total_items || 1)) * 100),
  );

  const activeIdx =
    pct >= 100 ? 3 : pct >= 40 ? 2 : pct >= 15 ? 1 : 0;

  return (
    <div role="status" className="space-y-3 rounded-lg border border-accent-500/25 bg-accent-500/5 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-content-primary">Análise em andamento</h3>
          <p className="text-xs text-content-muted">
            {STAGES[activeIdx]?.label ?? 'Processando'} — aguarde para revisar os achados
          </p>
        </div>
        <div className="text-right">
          <span className="tnum block font-mono text-xl font-semibold text-accent-400">{pct}%</span>
          <span className="tnum block font-mono text-xs text-content-muted">
            {analysis.analyzed_items} de {analysis.total_items} itens
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

      <ol className="flex flex-wrap items-center gap-2 pt-1">
        {STAGES.map((stage, idx) => {
          const Icon = stage.icon;
          const done = idx < activeIdx || pct >= 100;
          const current = idx === activeIdx && pct < 100;
          return (
            <li
              key={stage.id}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[11px] font-medium',
                done && 'border-green-500/30 bg-green-500/10 text-green-300',
                current && 'border-accent-500/40 bg-accent-500/15 text-accent-300',
                !done && !current && 'border-line-subtle text-content-subtle',
              )}
            >
              <Icon className="h-3 w-3" aria-hidden />
              {stage.label}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
