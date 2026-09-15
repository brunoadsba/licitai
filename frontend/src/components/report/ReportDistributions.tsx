'use client';

import { Badge } from '@/components/ui/Badge';
import { CATEGORY_LABELS, SEVERITY_LABELS } from '@/types';
import type { ReportResponse } from '@/types';
import { getCategoryTone, getSeverityTone } from '@/lib/badges';

/** Distribuição por categoria e severidade — extraído de `app/report/[id]/page.tsx`. */
export default function ReportDistributions({ report }: { report: ReportResponse }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div className="rounded-lg border border-line-subtle bg-surface/40 p-6">
        <h3 className="mb-4 text-sm font-semibold text-content-primary">Por Categoria</h3>
        <div className="space-y-3">
          {Object.entries(report.corrections_by_category).map(([cat, count]) => {
            const total = report.total_corrections || 1;
            const pct = Math.round((count / total) * 100);
            return (
              <div key={cat}>
                <div className="mb-1 flex items-center justify-between">
                  <Badge tone={getCategoryTone(cat)}>
                    {CATEGORY_LABELS[cat as keyof typeof CATEGORY_LABELS] || cat}
                  </Badge>
                  <span className="tnum text-sm text-content-muted">{count}</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="rounded-lg border border-line-subtle bg-surface/40 p-6">
        <h3 className="mb-4 text-sm font-semibold text-content-primary">Por Severidade</h3>
        <div className="space-y-3">
          {Object.entries(report.corrections_by_severity).map(([sev, count]) => {
            const total = report.total_corrections || 1;
            const pct = Math.round((count / total) * 100);
            return (
              <div key={sev}>
                <div className="mb-1 flex items-center justify-between">
                  <Badge tone={getSeverityTone(sev)}>
                    {SEVERITY_LABELS[sev as keyof typeof SEVERITY_LABELS] || sev}
                  </Badge>
                  <span className="tnum text-sm text-content-muted">{count}</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
