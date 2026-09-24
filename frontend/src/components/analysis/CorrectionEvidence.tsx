'use client';

import type { CorrectionResponse } from '@/types';

export default function CorrectionEvidence({
  correction,
}: {
  correction: CorrectionResponse;
}) {
  const ev = correction.evidence;
  if (!ev) return null;
  return (
    <div className="mt-3 space-y-2 border-t border-line-subtle pt-3 text-xs text-content-muted">
      <p className="font-semibold uppercase tracking-wider text-content-subtle">
        Evidência DE → PARA
      </p>
      {ev.de && (
        <p>
          <span className="font-medium text-content-secondary">DE: </span>
          {ev.de}
        </p>
      )}
      {ev.para && (
        <p>
          <span className="font-medium text-content-secondary">PARA: </span>
          {ev.para}
        </p>
      )}
      <p className="tnum">
        {[
          ev.corpus_version && `corpus ${ev.corpus_version.slice(0, 12)}`,
          ev.retrieval_run_id && `rastro ${ev.retrieval_run_id.slice(0, 8)}`,
          ev.grounded === false && 'trecho não ancorado',
          correction.reviewed_at && `revisado em ${correction.reviewed_at}`,
        ]
          .filter(Boolean)
          .join(' · ')}
      </p>
    </div>
  );
}
