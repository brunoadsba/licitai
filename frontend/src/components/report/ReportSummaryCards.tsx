'use client';

import { RISK_LABELS } from '@/types';
import type { ReportResponse } from '@/types';

function getRiskColor(risk: string | null) {
  const colors: Record<string, string> = {
    baixo: 'text-green-400',
    medio: 'text-yellow-400',
    alto: 'text-orange-400',
    critico: 'text-red-400',
  };
  return colors[risk || ''] || 'text-content-muted';
}

/** Cards-resumo (risco, total, data) — extraído de `app/report/[id]/page.tsx`. */
export default function ReportSummaryCards({ report }: { report: ReportResponse }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div className="rounded-lg border border-line-subtle bg-surface/40 p-6">
        <p className="mb-2 text-[11px] uppercase tracking-widest text-content-subtle">Risco de Impugnação</p>
        <p className={`text-2xl font-semibold tracking-tight ${getRiskColor(report.risk_level)}`}>
          {report.risk_level ? RISK_LABELS[report.risk_level] || report.risk_level : 'N/A'}
        </p>
      </div>

      <div className="rounded-lg border border-line-subtle bg-surface/40 p-6">
        <p className="mb-2 text-[11px] uppercase tracking-widest text-content-subtle">Total de Correções</p>
        <p className="tnum text-2xl font-semibold tracking-tight text-content-primary">
          {report.total_corrections}
        </p>
      </div>

      <div className="rounded-lg border border-line-subtle bg-surface/40 p-6">
        <p className="mb-2 text-[11px] uppercase tracking-widest text-content-subtle">Data da Análise</p>
        <p className="tnum text-lg font-semibold text-content-primary">
          {report.analyzed_at
            ? new Date(report.analyzed_at).toLocaleDateString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })
            : 'N/A'}
        </p>
      </div>
    </div>
  );
}
