'use client';

import type { Art6ChecklistItem } from '@/types';
import { Badge } from '@/components/ui/Badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/Tooltip';
import { HelpCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Art6ChecklistPanelProps {
  items: Art6ChecklistItem[];
  coverage?: number | null;
  meetsTarget?: boolean | null;
}

/** Painel Art. 6º XXIII — alíneas faltantes/incertas + cobertura estrutural. */
export default function Art6ChecklistPanel({
  items,
  coverage,
  meetsTarget,
}: Art6ChecklistPanelProps) {
  if (!items.length) return null;
  const gaps = items.filter((i) => i.status !== 'present');
  const present = items.length - gaps.length;
  const pct =
    coverage != null
      ? Math.round(coverage * 100)
      : Math.round((present / items.length) * 100);
  const ok = meetsTarget ?? pct >= 90;

  const alineaHint = items
    .map((i) => `${i.alinea}) ${i.label}`)
    .join(' · ');

  return (
    <TooltipProvider delayDuration={200}>
      <div
        className={cn(
          'rounded-lg border p-4',
          gaps.length === 0
            ? 'border-green-500/25 bg-green-500/5'
            : 'border-amber-500/25 bg-amber-500/5',
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="flex items-center gap-1.5 text-sm font-medium text-content-primary">
              Art. 6º, XXIII — cobertura {pct}%
              {gaps.length === 0
                ? ` (${present}/${items.length})`
                : ` · ${gaps.length} alínea(s) a revisar`}
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className="inline-flex text-content-subtle outline-none hover:text-content-muted focus-visible:ring-2 focus-visible:ring-accent-500/60"
                    aria-label="O que é Art. 6º, XXIII"
                  >
                    <HelpCircle className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-sm">
                  Checklist estrutural do Termo de Referência (alíneas a–j). Meta ≥90%.
                  Confirme no texto antes de colar no SEI.
                  {alineaHint ? ` Itens: ${alineaHint}` : ''}
                </TooltipContent>
              </Tooltip>
            </p>
            <p className="mt-1 text-xs text-content-muted">
              {gaps.length === 0
                ? `Checklist a–j aparenta completo. Meta ≥90%${ok ? ' atingida.' : '.'}`
                : 'Faltantes entram em “Revisar agora”. Confirme no texto antes de colar no SEI.'}
            </p>
          </div>
        </div>
        {gaps.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2">
            {gaps.map((g) => (
              <li key={g.key}>
                <Badge tone={g.status === 'missing' ? 'critical' : 'medium'}>
                  {g.alinea}) {g.label}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </div>
    </TooltipProvider>
  );
}
