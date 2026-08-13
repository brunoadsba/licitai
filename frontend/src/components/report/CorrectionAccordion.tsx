import { useState } from 'react';
import type { CorrectionResponse } from '@/types';
import { CATEGORY_LABELS, SEVERITY_LABELS } from '@/types';
import { getCategoryBadge, getSeverityBadge } from '@/lib/badges';
import { useCopy } from '@/lib/useCopy';

interface CorrectionAccordionProps {
  corrections: CorrectionResponse[];
  total: number;
}

/**
 * Lista expandível de correções do relatório, com cópia DE → PARA e justificativa para o SEI.
 */
export default function CorrectionAccordion({ corrections, total }: CorrectionAccordionProps) {
  const { copy, isCopied } = useCopy();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  function toggleCorrection(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-white">Todas as Correções ({total})</h2>

      {corrections.map((correction, idx) => {
        const isExpanded = expanded.has(correction.id);

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
                        onClick={() => copy(correction.suggested_text, `rep_para_${correction.id}`)}
                        className="px-2 py-1 rounded bg-green-500/20 hover:bg-green-500/30 text-green-300 text-xs font-semibold flex items-center gap-1 border border-green-500/30"
                      >
                        {isCopied(`rep_para_${correction.id}`) ? '✓ Copiado!' : '📋 Copiar para SEI'}
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
                        copy(
                          `${correction.justification}${correction.legal_basis ? ` (Fundamento: ${correction.legal_basis})` : ''}`,
                          `rep_just_${correction.id}`
                        )
                      }
                      className="text-[11px] text-primary-400/80 hover:text-primary-300 underline"
                    >
                      {isCopied(`rep_just_${correction.id}`) ? 'Copiado!' : 'Copiar Justificativa'}
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
  );
}
