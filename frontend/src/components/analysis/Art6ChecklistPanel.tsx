'use client';

import type { Art6ChecklistItem } from '@/types';
import { Badge } from '@/components/ui/Badge';

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

  if (gaps.length === 0) {
    return (
      <div className="glass-card border-green-500/20 p-4">
        <p className="text-sm font-medium text-content-primary">
          Art. 6º, XXIII — cobertura {pct}% ({present}/{items.length})
        </p>
        <p className="mt-1 text-xs text-content-muted">
          Checklist a–j aparenta completo neste TR (heurística estrutural). Meta ≥90%
          {ok ? ' atingida.' : '.'}
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card border-amber-500/20 p-4">
      <p className="text-sm font-medium text-content-primary">
        Art. 6º, XXIII — cobertura {pct}% · {gaps.length} alínea(s) a revisar
      </p>
      <p className="mt-1 text-xs text-content-muted">
        Meta estrutural ≥90%. Faltantes entram na fila Prioridade. Confirme no texto
        antes de colar no SEI.
      </p>
      <ul className="mt-3 flex flex-wrap gap-2">
        {gaps.map((g) => (
          <li key={g.key}>
            <Badge tone={g.status === 'missing' ? 'critical' : 'medium'}>
              {g.alinea}) {g.label}
            </Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}
