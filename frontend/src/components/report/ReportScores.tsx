'use client';

import ScoreGauge from '@/components/report/ScoreGauge';
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

/** Gauges de pontuação + frase-resumo — extraído de `app/report/[id]/page.tsx`. */
export default function ReportScores({ report }: { report: ReportResponse }) {
  const overallScore = report.scores.find((s) => s.label === 'Nota Geral') ?? report.scores[0] ?? null;
  const criticalCount = report.corrections_by_severity?.critico ?? 0;
  const highCount = report.corrections_by_severity?.alto ?? 0;
  const totalCorrections = report.total_corrections ?? 0;
  const severityParts: string[] = [];
  if (criticalCount > 0) {
    severityParts.push(`${criticalCount} ${criticalCount === 1 ? 'achado crítico' : 'achados críticos'}`);
  }
  if (highCount > 0) {
    severityParts.push(`${highCount} de alto risco`);
  }
  const severidade = severityParts.length > 0 ? `, com ${severityParts.join(' e ')}` : '';
  const recomendacoes =
    totalCorrections === 0
      ? ' e nenhuma recomendação pendente'
      : ` e ${totalCorrections} ${totalCorrections === 1 ? 'recomendação no total' : 'recomendações no total'}`;

  return (
    <div className="rounded-lg border border-line-subtle bg-surface/40 p-6 sm:p-8">
      <h2 className="mb-6 text-lg font-semibold tracking-tight text-content-primary">Pontuação</h2>
      <div className="flex flex-wrap items-center justify-around gap-6">
        {report.scores.map((score) => (
          <ScoreGauge key={score.label} score={score.score} label={score.label} />
        ))}
      </div>
      {overallScore && overallScore.score !== null ? (
        <p className="tnum mt-6 border-t border-line-subtle pt-4 text-center text-sm">
          <span className={`font-semibold ${getRiskColor(report.risk_level)}`}>
            {overallScore.score.toFixed(1)}/10
          </span>
          <span className="text-content-muted">
            {' — '}
            {report.risk_level ? RISK_LABELS[report.risk_level].toLowerCase() : 'sem classificação de risco'}
            {severidade}
            {recomendacoes}
          </span>
          {report.tokens_estimated && (
            <span className="ml-2 text-xs text-content-subtle">· ~{report.tokens_estimated.toLocaleString('pt-BR')} tokens</span>
          )}
        </p>
      ) : (
        <p className="mt-6 border-t border-line-subtle pt-4 text-center text-sm text-content-muted">
          Análise sem pontuação — consulte o parecer final.
        </p>
      )}
    </div>
  );
}
