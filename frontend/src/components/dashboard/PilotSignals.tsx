'use client';

import Link from 'next/link';
import { ChevronDown } from 'lucide-react';
import type { MetricsSnapshot, PendingSummaryResponse } from '@/lib/api';

export function PendingReviewList({ pending }: { pending: PendingSummaryResponse }) {
  if (!pending.items.length) return null;
  return (
    <div className="space-y-3 rounded-lg border border-line-subtle bg-surface/40 p-4">
      <p className="text-sm font-medium text-content-primary">Para revisar agora</p>
      <ul className="space-y-2">
        {pending.items.slice(0, 8).map((item) => (
          <li key={item.document_id}>
            <Link
              href={`/analysis/${item.document_id}`}
              className="flex items-center justify-between gap-3 rounded-lg border border-line-subtle px-3 py-2 text-sm outline-none hover:bg-white/[0.04] focus-visible:ring-2 focus-visible:ring-accent-500/60"
            >
              <span className="truncate text-content-primary">{item.filename}</span>
              <span className="tnum shrink-0 text-xs text-amber-400">
                {item.pending_priority} pendente(s)
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function PilotHealthPanel({
  metrics,
  open,
  onToggle,
}: {
  metrics: MetricsSnapshot | null;
  open: boolean;
  onToggle: () => void;
}) {
  const counters = metrics?.counters ?? {};
  return (
    <div className="overflow-hidden rounded-lg border border-line-subtle bg-surface/40">
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm outline-none hover:bg-white/[0.03] focus-visible:ring-2 focus-visible:ring-accent-500/60"
        onClick={onToggle}
        aria-expanded={open}
      >
        <span className="font-medium text-content-primary">Saúde do piloto</span>
        <ChevronDown
          className={`h-4 w-4 text-content-subtle transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>
      {open && (
        <div className="border-t border-line-subtle px-4 py-3 text-xs text-content-muted">
          {metrics ? (
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <dt>llm_errors</dt>
                <dd className="tnum text-content-primary">{counters.llm_errors ?? 0}</dd>
              </div>
              <div>
                <dt>job_errors</dt>
                <dd className="tnum text-content-primary">{counters.job_errors ?? 0}</dd>
              </div>
              <div>
                <dt>analyses</dt>
                <dd className="tnum text-content-primary">
                  {counters.analysis_completed ?? metrics.analysis_duration_count ?? 0}
                </dd>
              </div>
              <div>
                <dt>review rejeitada</dt>
                <dd className="tnum text-content-primary">{counters.review_rejected ?? 0}</dd>
              </div>
            </dl>
          ) : (
            <p>Métricas indisponíveis (backend off?).</p>
          )}
        </div>
      )}
    </div>
  );
}
