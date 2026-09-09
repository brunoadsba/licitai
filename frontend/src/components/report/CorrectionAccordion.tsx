'use client';

import { useState } from 'react';
import type { CorrectionResponse } from '@/types';
import { CATEGORY_LABELS, SEVERITY_LABELS } from '@/types';
import { getCategoryBadge, getSeverityBadge } from '@/lib/badges';
import { useCopy } from '@/lib/useCopy';
import { isSeiCopyAllowed } from '@/components/analysis/CorrectionCard';
import { Check, ChevronDown, ClipboardCopy, TriangleAlert } from 'lucide-react';

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
      <h2 className="tnum text-lg font-semibold tracking-tight text-content-primary">
        Todas as Correções ({total})
      </h2>

      {corrections.map((correction, idx) => {
        const isExpanded = expanded.has(correction.id);
        const canCopyPara = isSeiCopyAllowed(correction.review_status);

        return (
          <div
            key={correction.id}
            className="glass-card animate-slide-up overflow-hidden"
            style={{ animationDelay: `${Math.min(idx, 8) * 30}ms` }}
          >
            {/* Header (clicável) */}
            <button
              onClick={() => toggleCorrection(correction.id)}
              aria-expanded={isExpanded}
              className="flex w-full items-center justify-between gap-3 p-5 text-left outline-none transition-colors hover:bg-white/[0.02] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent-500/60"
            >
              <div className="flex min-w-0 flex-wrap items-center gap-2.5 sm:flex-nowrap">
                <span className="tnum shrink-0 font-mono text-sm text-content-subtle">#{idx + 1}</span>
                <span className={`badge ${getCategoryBadge(correction.category)}`}>
                  {CATEGORY_LABELS[correction.category] || correction.category}
                </span>
                <span className={`badge ${getSeverityBadge(correction.severity)}`}>
                  {SEVERITY_LABELS[correction.severity] || correction.severity}
                </span>
                <p className="truncate text-sm text-content-secondary">{correction.problem}</p>
              </div>
              <ChevronDown
                className={`h-4 w-4 shrink-0 text-content-subtle transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                aria-hidden
              />
            </button>

            {/* Conteúdo expandido */}
            {isExpanded && (
              <div className="animate-fade-in space-y-4 border-t border-line-subtle px-5 pb-5 pt-4">
                <p className="text-sm text-content-muted">{correction.situation}</p>

                <div className="space-y-2">
                  <div className="diff-removed">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-red-400/70">
                      DE (original)
                    </p>
                    <p className="text-sm text-red-300/90">{correction.original_text}</p>
                  </div>
                  <div className="diff-added group relative">
                    <div className="mb-1 flex items-center justify-between">
                      <p className="text-xs font-semibold uppercase tracking-wider text-green-400/70">
                        PARA (sugerido)
                      </p>
                      <button
                        type="button"
                        disabled={!canCopyPara}
                        title={
                          canCopyPara
                            ? undefined
                            : 'Disponível apenas para correções aprovadas ou ajustadas'
                        }
                        onClick={() => {
                          if (!canCopyPara) return;
                          copy(correction.suggested_text, `rep_para_${correction.id}`);
                        }}
                        className="inline-flex items-center gap-1 rounded-md border border-green-500/30 bg-green-500/20 px-2 py-1 text-xs font-medium text-green-300 outline-none transition-colors hover:bg-green-500/30 focus-visible:ring-2 focus-visible:ring-green-500/60 disabled:cursor-not-allowed disabled:border-line-subtle disabled:bg-canvas/40 disabled:text-content-subtle disabled:hover:bg-canvas/40"
                      >
                        {isCopied(`rep_para_${correction.id}`) ? (
                          <>
                            <Check className="h-3 w-3" aria-hidden /> Copiado!
                          </>
                        ) : (
                          <>
                            <ClipboardCopy className="h-3 w-3" aria-hidden /> Copiar para SEI
                          </>
                        )}
                      </button>
                    </div>
                    <p className="text-sm text-green-300/90">{correction.suggested_text}</p>
                  </div>
                </div>

                <div className="rounded-lg border border-line-subtle bg-canvas/40 p-3">
                  <div className="mb-1 flex items-center justify-between">
                    <p className="text-xs font-semibold uppercase tracking-wider text-content-subtle">
                      Justificativa
                    </p>
                    <button
                      onClick={() =>
                        copy(
                          `${correction.justification}${correction.legal_basis ? ` (Fundamento: ${correction.legal_basis})` : ''}`,
                          `rep_just_${correction.id}`,
                        )
                      }
                      className="text-[11px] text-accent-400/80 underline outline-none hover:text-accent-300 focus-visible:ring-2 focus-visible:ring-accent-500/60"
                    >
                      {isCopied(`rep_just_${correction.id}`) ? 'Copiado!' : 'Copiar Justificativa'}
                    </button>
                  </div>
                  <p className="text-sm text-content-muted">{correction.justification}</p>
                  {correction.legal_basis && (
                    <p className="tnum mt-2 font-mono text-xs text-accent-400">{correction.legal_basis}</p>
                  )}
                </div>

                <p className="flex items-start gap-1.5 text-xs text-yellow-400/70">
                  <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                  {correction.risk}
                </p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
