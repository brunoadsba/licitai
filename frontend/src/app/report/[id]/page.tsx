'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getReport } from '@/lib/api';
import type { ReportResponse } from '@/types';
import { CATEGORY_LABELS, SEVERITY_LABELS, RISK_LABELS } from '@/types';

function ScoreGauge({ score, label }: { score: number | null; label: string }) {
  const value = score ?? 0;
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 10) * circumference;

  const getColor = (s: number) => {
    if (s >= 8) return '#22c55e';
    if (s >= 6) return '#eab308';
    if (s >= 4) return '#f97316';
    return '#ef4444';
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-28 h-28">
        <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50" cy="50" r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="8"
          />
          <circle
            cx="50" cy="50" r={radius}
            fill="none"
            stroke={score !== null ? getColor(value) : 'rgba(255,255,255,0.1)'}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={score !== null ? offset : circumference}
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-white">
            {score !== null ? score.toFixed(1) : '—'}
          </span>
        </div>
      </div>
      <span className="text-xs text-gray-400 text-center">{label}</span>
    </div>
  );
}

export default function ReportPage() {
  const params = useParams();
  const analysisId = params.id as string;

  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCorrections, setExpandedCorrections] = useState<Set<string>>(new Set());
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

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

  function handleCopy(text: string, key: string) {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  }

  function toggleCorrection(id: string) {
    setExpandedCorrections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function getRiskColor(risk: string | null) {
    const colors: Record<string, string> = {
      baixo: 'text-green-400',
      medio: 'text-yellow-400',
      alto: 'text-orange-400',
      critico: 'text-red-400',
    };
    return colors[risk || ''] || 'text-gray-400';
  }

  function getCategoryBadge(category: string) {
    const classes: Record<string, string> = {
      juridica: 'badge-juridica',
      tecnica: 'badge-tecnica',
      redacao: 'badge-redacao',
      estrutural: 'badge-estrutural',
    };
    return classes[category] || 'badge-info';
  }

  function getSeverityBadge(severity: string) {
    const classes: Record<string, string> = {
      info: 'badge-info',
      baixo: 'badge-baixo',
      medio: 'badge-medio',
      alto: 'badge-alto',
      critico: 'badge-critico',
    };
    return classes[severity] || 'badge-info';
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="skeleton h-12 w-64" />
        <div className="grid grid-cols-5 gap-4">
          {[1, 2, 3, 4, 5].map((i) => <div key={i} className="skeleton h-40" />)}
        </div>
        <div className="skeleton h-64" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="glass-card p-12 text-center">
        <p className="text-red-400">{error || 'Relatório não encontrado.'}</p>
        <Link href="/" className="btn-primary mt-4 inline-flex">Voltar</Link>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
            <Link href="/" className="hover:text-gray-300 transition-colors">Painel</Link>
            <span>›</span>
            <Link href={`/analysis/${report.document_id}`} className="hover:text-gray-300 transition-colors">Análise</Link>
            <span>›</span>
            <span className="text-gray-400">Relatório</span>
          </div>
          <h1 className="text-2xl font-bold text-white">Relatório de Análise</h1>
          <p className="text-gray-500 text-sm mt-1">{report.document_name}</p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/analysis/${report.document_id}`}
            className="btn-secondary"
          >
            ← Voltar à Análise
          </Link>
        </div>
      </div>

      {/* Gauges de pontuação */}
      <div className="glass-card p-8">
        <h2 className="text-lg font-semibold text-white mb-6">Pontuação</h2>
        <div className="flex items-center justify-around flex-wrap gap-6">
          {report.scores.map((score) => (
            <ScoreGauge
              key={score.label}
              score={score.score}
              label={score.label}
            />
          ))}
        </div>
      </div>

      {/* Resumo em cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Risco */}
        <div className="glass-card p-6">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Risco de Impugnação</p>
          <p className={`text-2xl font-bold ${getRiskColor(report.risk_level)}`}>
            {report.risk_level ? (RISK_LABELS[report.risk_level] || report.risk_level) : 'N/A'}
          </p>
        </div>

        {/* Total de correções */}
        <div className="glass-card p-6">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Total de Correções</p>
          <p className="text-2xl font-bold text-white">{report.total_corrections}</p>
        </div>

        {/* Data */}
        <div className="glass-card p-6">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Data da Análise</p>
          <p className="text-lg font-semibold text-white">
            {report.analyzed_at
              ? new Date(report.analyzed_at).toLocaleDateString('pt-BR', {
                  day: '2-digit', month: '2-digit', year: 'numeric',
                  hour: '2-digit', minute: '2-digit',
                })
              : 'N/A'}
          </p>
        </div>
      </div>

      {/* Distribuição por categoria e severidade */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass-card p-6">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Por Categoria</h3>
          <div className="space-y-3">
            {Object.entries(report.corrections_by_category).map(([cat, count]) => {
              const total = report.total_corrections || 1;
              const pct = Math.round((count / total) * 100);
              return (
                <div key={cat}>
                  <div className="flex items-center justify-between mb-1">
                    <span className={`badge ${getCategoryBadge(cat)}`}>
                      {CATEGORY_LABELS[cat as keyof typeof CATEGORY_LABELS] || cat}
                    </span>
                    <span className="text-sm text-gray-400">{count}</span>
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
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Por Severidade</h3>
          <div className="space-y-3">
            {Object.entries(report.corrections_by_severity).map(([sev, count]) => {
              const total = report.total_corrections || 1;
              const pct = Math.round((count / total) * 100);
              return (
                <div key={sev}>
                  <div className="flex items-center justify-between mb-1">
                    <span className={`badge ${getSeverityBadge(sev)}`}>
                      {SEVERITY_LABELS[sev as keyof typeof SEVERITY_LABELS] || sev}
                    </span>
                    <span className="text-sm text-gray-400">{count}</span>
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
        <div className="glass-card p-6 glow">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <svg className="w-5 h-5 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
              </svg>
              Parecer Final
            </h2>
            <button
              onClick={() => handleCopy(report.final_opinion || '', 'final_opinion')}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary-600/20 hover:bg-primary-600/30 text-primary-300 border border-primary-500/30 flex items-center gap-1.5 transition-all"
            >
              {copiedKey === 'final_opinion' ? (
                <>
                  <svg className="w-3.5 h-3.5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  Parecer Copiado!
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.757c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                  </svg>
                  Copiar Parecer para o SEI
                </>
              )}
            </button>
          </div>
          <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
            {report.final_opinion}
          </p>
        </div>
      )}

      {/* Lista expandível de correções */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-white">Todas as Correções ({report.total_corrections})</h2>

        {report.corrections.map((correction, idx) => {
          const isExpanded = expandedCorrections.has(correction.id);

          return (
            <div key={correction.id} className="glass-card overflow-hidden animate-slide-up" style={{ animationDelay: `${idx * 30}ms` }}>
              {/* Header (clicável) */}
              <button
                onClick={() => toggleCorrection(correction.id)}
                className="w-full p-5 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-sm text-gray-500 font-mono shrink-0">#{idx + 1}</span>
                  <span className={`badge ${getCategoryBadge(correction.category)}`}>
                    {CATEGORY_LABELS[correction.category] || correction.category}
                  </span>
                  <span className={`badge ${getSeverityBadge(correction.severity)}`}>
                    {SEVERITY_LABELS[correction.severity] || correction.severity}
                  </span>
                  <p className="text-sm text-gray-300 truncate">{correction.problem}</p>
                </div>
                <svg
                  className={`w-4 h-4 text-gray-500 shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                </svg>
              </button>

              {/* Conteúdo expandido */}
              {isExpanded && (
                <div className="px-5 pb-5 border-t border-white/[0.04] pt-4 space-y-4 animate-fade-in">
                  <p className="text-sm text-gray-400">{correction.situation}</p>

                  <div className="space-y-2">
                    <div className="diff-removed">
                      <p className="text-xs text-red-400/70 font-semibold uppercase tracking-wider mb-1">DE (original)</p>
                      <p className="text-sm text-red-300/90">{correction.original_text}</p>
                    </div>
                    <div className="diff-added relative group">
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-xs text-green-400/70 font-semibold uppercase tracking-wider">PARA (sugerido)</p>
                        <button
                          onClick={() => handleCopy(correction.suggested_text, `rep_para_${correction.id}`)}
                          className="px-2 py-1 rounded bg-green-500/20 hover:bg-green-500/30 text-green-300 text-xs font-semibold flex items-center gap-1 border border-green-500/30"
                        >
                          {copiedKey === `rep_para_${correction.id}` ? '✓ Copiado!' : '📋 Copiar para SEI'}
                        </button>
                      </div>
                      <p className="text-sm text-green-300/90">{correction.suggested_text}</p>
                    </div>
                  </div>

                  <div className="bg-surface-900/30 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider">Justificativa</p>
                      <button
                        onClick={() =>
                          handleCopy(
                            `${correction.justification}${correction.legal_basis ? ` (Fundamento: ${correction.legal_basis})` : ''}`,
                            `rep_just_${correction.id}`
                          )
                        }
                        className="text-[11px] text-primary-400/80 hover:text-primary-300 underline"
                      >
                        {copiedKey === `rep_just_${correction.id}` ? 'Copiado!' : 'Copiar Justificativa'}
                      </button>
                    </div>
                    <p className="text-sm text-gray-400">{correction.justification}</p>
                    {correction.legal_basis && (
                      <p className="text-xs text-primary-400 mt-2 font-mono">📋 {correction.legal_basis}</p>
                    )}
                  </div>

                  <p className="text-xs text-yellow-400/70 flex items-center gap-1">
                    <span>⚠️</span> {correction.risk}
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
