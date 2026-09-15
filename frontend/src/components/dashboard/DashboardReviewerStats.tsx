'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getMetricsSnapshot } from '@/lib/api';

export default function DashboardReviewerStats() {
  const [stats, setStats] = useState<{ accepted: number; overridden: number; tracked: number } | null>(null);

  useEffect(() => {
    getMetricsSnapshot()
      .then((m) => {
        const c = m.counters;
        const tracked = c.review_suggestion_tracked ?? 0;
        if (tracked === 0) return;
        setStats({
          accepted: c.review_suggestion_accepted ?? 0,
          overridden: c.review_suggestion_overridden ?? 0,
          tracked,
        });
      })
      .catch(() => {});
  }, []);

  if (!stats) return null;
  const rate = Math.round((stats.accepted / stats.tracked) * 100);

  return (
    <div className="rounded-lg border border-line-subtle bg-surface/30 px-4 py-3" data-testid="dashboard-reviewer-stats">
      <p className="text-xs font-semibold uppercase tracking-wider text-content-subtle">Revisor-assistente</p>
      <p className="mt-1 tnum text-sm text-content-secondary">
        <span className="font-semibold text-content-primary">{rate}%</span> aceitação · {stats.accepted} aceitas · {stats.overridden} sobrepostas
      </p>
      <Link href="/guia" className="mt-1 inline-block text-xs text-content-subtle hover:text-accent-400">
        Como usar o modo guiado →
      </Link>
    </div>
  );
}
