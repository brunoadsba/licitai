'use client';

import { useEffect, useState } from 'react';
import { getMetricsSnapshot } from '@/lib/api';

export default function ReportSuggestionStats() {
  const [data, setData] = useState<{ accepted: number; overridden: number; tracked: number } | null>(null);

  useEffect(() => {
    getMetricsSnapshot()
      .then((m) => {
        const c = m.counters;
        setData({
          accepted: c.review_suggestion_accepted ?? 0,
          overridden: c.review_suggestion_overridden ?? 0,
          tracked: c.review_suggestion_tracked ?? 0,
        });
      })
      .catch(() => {});
  }, []);

  if (!data || data.tracked === 0) return null;
  const rate = data.tracked > 0 ? Math.round((data.accepted / data.tracked) * 100) : 0;

  return (
    <div className="rounded-lg border border-line-subtle bg-surface/40 p-4" data-testid="suggestion-stats">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-content-subtle">Revisor-assistente · métrica</h3>
      <p className="tnum text-sm text-content-secondary">
        <span className="font-semibold text-content-primary">{rate}%</span> de aceitação · {data.accepted} aceitas · {data.overridden} sobrepostas · {data.tracked} rastreadas
      </p>
      <p className="mt-1 text-xs text-content-muted">Consultivo: você decide; nada vai ao SEI sem aprovação.</p>
    </div>
  );
}
