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
import {
  art6BadgeLabel,
  art6PanelSubtitle,
  art6PanelTitle,
  art6TooltipBody,
} from '@/lib/copy/elaborador';

interface Art6ChecklistPanelProps {
  items: Art6ChecklistItem[];
  coverage?: number | null;
  meetsTarget?: boolean | null;
}

/** Painel das partes obrigatórias do TR (Art. 6º a–j). */
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

  return (
    <TooltipProvider delayDuration={200}>
      <div
        data-testid="art6-panel"
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
              {art6PanelTitle(pct)}
              {gaps.length === 0 ? ` (${present}/${items.length})` : null}
              {!ok && gaps.length === 0 ? ' · meta ~90%' : null}
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className="inline-flex text-content-subtle outline-none hover:text-content-muted focus-visible:ring-2 focus-visible:ring-accent-500/60"
                    aria-label="O que são as partes obrigatórias do TR"
                  >
                    <HelpCircle className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-sm">
                  {art6TooltipBody(items)}
                </TooltipContent>
              </Tooltip>
            </p>
            <p className="mt-1 text-xs text-content-muted">
              {art6PanelSubtitle(gaps.length)}
            </p>
          </div>
        </div>
        {gaps.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2">
            {gaps.map((g) => (
              <li key={g.key}>
                <Badge tone={g.status === 'missing' ? 'critical' : 'medium'}>
                  {art6BadgeLabel(g.alinea, g.key, g.label)}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </div>
    </TooltipProvider>
  );
}
