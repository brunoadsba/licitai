'use client';

import { Badge } from '@/components/ui/Badge';
import type { ReportResponse } from '@/types';
import {
  art6BadgeLabel,
  art6PanelTitle,
} from '@/lib/copy/elaborador';

/** Painel Art. 6º do relatório — extraído de `app/report/[id]/page.tsx`. */
export default function ReportArt6({ report }: { report: ReportResponse }) {
  if ((report.art6_checklist ?? []).length === 0) return null;
  return (
    <div
      className={`rounded-lg border border-line-subtle bg-surface/40 space-y-2 p-4 ${
        (report.art6_meets_target ?? false)
          ? 'border-green-500/20'
          : 'border-amber-500/20'
      }`}
    >
      <h2 className="text-lg font-semibold tracking-tight text-content-primary">
        {art6PanelTitle(Math.round((report.art6_coverage ?? 0) * 100))}
        {report.art6_meets_target ? '' : ' · meta ~90%'}
      </h2>
      <p className="text-xs text-content-muted">
        {report.art6_meets_target
          ? 'As 10 partes mínimas da lei parecem presentes.'
          : 'Confira as partes faltantes abaixo antes de usar o export no SEI.'}
      </p>
      {(report.art6_checklist ?? []).some((i) => i.status !== 'present') && (
        <ul className="flex flex-wrap gap-2">
          {(report.art6_checklist ?? [])
            .filter((i) => i.status !== 'present')
            .map((g) => (
              <li key={g.key}>
                <Badge tone={g.status === 'missing' ? 'critical' : 'medium'}>
                  {art6BadgeLabel(g.alinea, g.key, g.label)}
                </Badge>
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}
