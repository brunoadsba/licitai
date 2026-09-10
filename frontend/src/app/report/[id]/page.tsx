'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Check, ClipboardCopy, FileDown, FileText } from 'lucide-react';
import { getReport } from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';
import ScoreGauge from '@/components/report/ScoreGauge';
import CorrectionAccordion from '@/components/report/CorrectionAccordion';
import { useCopy } from '@/lib/useCopy';
import type { ReportResponse } from '@/types';
import { CATEGORY_LABELS, SEVERITY_LABELS, RISK_LABELS } from '@/types';
import { getCategoryTone, getSeverityTone } from '@/lib/badges';

function getRiskColor(risk: string | null) {
  const colors: Record<string, string> = {
    baixo: 'text-green-400',
    medio: 'text-yellow-400',
    alto: 'text-orange-400',
    critico: 'text-red-400',
  };
  return colors[risk || ''] || 'text-content-muted';
}

export default function ReportPage() {
  const params = useParams();
  const analysisId = params.id as string;

  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { copy, isCopied } = useCopy();

  useEffect(() => {
    async function load() {
      try {
        const data = await getReport(analysisId);
        setReport(data);
      } catch {
        setError('Erro ao carregar relatório.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [analysisId]);

  if (loading) {
    return (
      <div className="animate-fade-in space-y-6">
        <Skeleton className="h-12 w-64" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (error) {
    const errInfo = getErrorMessage(error, 'analysis');
    return (
      <div className="animate-fade-in space-y-4">
        <AlertBanner variant="error" title={errInfo.title}>
          {errInfo.message}
        </AlertBanner>
        <Link href="/">
          <Button>Voltar ao Painel</Button>
        </Link>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="glass-card p-12 text-center">
        <p className="text-content-muted">Relatório não encontrado.</p>
        <Link href="/" className="mt-4 inline-flex">
          <Button>Voltar</Button>
        </Link>
      </div>
    );
  }

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
    <div className="print-root animate-fade-in space-y-8">
      {/* Cabeçalho */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="mb-1 flex items-center gap-1.5 text-xs text-content-subtle no-print">
            <Link href="/" className="outline-none transition-colors hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60">
              Painel
            </Link>
            <span aria-hidden>/</span>
            <Link
              href={`/analysis/${report.document_id}`}
              className="outline-none transition-colors hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
            >
              Análise
            </Link>
            <span aria-hidden>/</span>
            <span className="text-content-muted">Relatório</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-content-primary">Relatório de Análise</h1>
          <p className="mt-1 text-sm text-content-muted">{report.document_name}</p>
        </div>

        <div className="no-print flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => window.print()}
            title="Abre o diálogo de impressão do navegador (Salvar como PDF)"
          >
            <FileDown className="h-4 w-4" aria-hidden />
            Exportar PDF
          </Button>
          <Link href={`/analysis/${report.document_id}`}>
            <Button variant="secondary">
              <ArrowLeft className="h-4 w-4" aria-hidden />
              Voltar à Análise
            </Button>
          </Link>
        </div>
      </div>

      {/* Gauges de pontuação */}
      <div className="glass-card p-6 sm:p-8">
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

      {/* Resumo em cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="glass-card p-6">
          <p className="mb-2 text-[11px] uppercase tracking-widest text-content-subtle">Risco de Impugnação</p>
          <p className={`text-2xl font-semibold tracking-tight ${getRiskColor(report.risk_level)}`}>
            {report.risk_level ? RISK_LABELS[report.risk_level] || report.risk_level : 'N/A'}
          </p>
        </div>

        <div className="glass-card p-6">
          <p className="mb-2 text-[11px] uppercase tracking-widest text-content-subtle">Total de Correções</p>
          <p className="tnum text-2xl font-semibold tracking-tight text-content-primary">
            {report.total_corrections}
          </p>
        </div>

        <div className="glass-card p-6">
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

      {/* Distribuição por categoria e severidade */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="glass-card p-6">
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

        <div className="glass-card p-6">
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

      {/* Parecer final (com botão de copiar para o SEI) */}
      {report.final_opinion && (
        <div className="glass-card border-accent-500/20 p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 text-lg font-semibold tracking-tight text-content-primary">
              <FileText className="h-5 w-5 text-accent-400" aria-hidden />
              Parecer Final
            </h2>
            <button
              onClick={() => copy(report.final_opinion || '', 'final_opinion')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-accent-500/30 bg-accent-500/15 px-3 py-1.5 text-xs font-medium text-accent-400 outline-none transition-colors hover:bg-accent-500/25 focus-visible:ring-2 focus-visible:ring-accent-500/60"
            >
              {isCopied('final_opinion') ? (
                <>
                  <Check className="h-3.5 w-3.5 text-green-400" aria-hidden />
                  Parecer Copiado!
                </>
              ) : (
                <>
                  <ClipboardCopy className="h-3.5 w-3.5" aria-hidden />
                  Copiar Parecer para o SEI
                </>
              )}
            </button>
          </div>
          <p className="whitespace-pre-wrap leading-relaxed text-content-secondary">{report.final_opinion}</p>
        </div>
      )}

      {/* Lista expandível de correções */}
      <CorrectionAccordion corrections={report.corrections} total={report.total_corrections} />
    </div>
  );
}
