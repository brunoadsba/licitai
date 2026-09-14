'use client';

import { useState } from 'react';
import type { CorrectionResponse, ReviewStatus } from '@/types';
import { SEVERITY_LABELS } from '@/types';
import { getSeverityTone } from '@/lib/badges';
import type { Tone } from '@/lib/badges';
import { Badge } from '@/components/ui/Badge';
import { useCopy } from '@/lib/useCopy';
import CorrectionReviewActions from '@/components/analysis/CorrectionReviewActions';
import { formatOriginalForDisplay } from '@/lib/diffDisplay';
import { hasPlaceholderText } from '@/lib/placeholderText';
import { Check, ChevronDown, ClipboardCopy, TriangleAlert } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CorrectionCardProps {
  correction: CorrectionResponse;
  index: number;
  onReviewUpdated?: (correction: CorrectionResponse) => void;
}

const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
  pendente: 'Pendente',
  aprovada: 'Aprovada',
  rejeitada: 'Rejeitada',
  ajustada: 'Ajustada',
};

const REVIEW_STATUS_TONE: Record<ReviewStatus, Tone> = {
  pendente: 'medium',
  aprovada: 'low',
  rejeitada: 'critical',
  ajustada: 'low',
};

/** Correções copiáveis para o SEI: apenas aprovada ou ajustada. */
export function isSeiCopyAllowed(status: CorrectionResponse['review_status']): boolean {
  return status === 'aprovada' || status === 'ajustada';
}

/**
 * Card DE → PARA de uma correção, com revisão humana e cópia para o SEI.
 */
export default function CorrectionCard({
  correction,
  index,
  onReviewUpdated,
}: CorrectionCardProps) {
  const { copy, isCopied } = useCopy();
  const reviewStatus = correction.review_status ?? 'pendente';
  const canCopyPara = isSeiCopyAllowed(reviewStatus);
  const [fundOpen, setFundOpen] = useState(false);
  const originalDisplay = formatOriginalForDisplay(
    correction.original_text,
    correction.suggested_text,
  );
  const needsAdjust =
    reviewStatus === 'pendente' && hasPlaceholderText(correction.suggested_text);

  return (
    <div
      className="animate-slide-up rounded-lg border border-line-subtle bg-surface/50 p-5"
      style={{ animationDelay: `${Math.min(index, 6) * 50}ms` }}
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge tone={getSeverityTone(correction.severity)}>
          {SEVERITY_LABELS[correction.severity] || correction.severity}
        </Badge>
        <Badge tone={REVIEW_STATUS_TONE[reviewStatus]}>
          {REVIEW_STATUS_LABELS[reviewStatus]}
        </Badge>
      </div>

      <p className="mb-4 text-sm text-content-secondary">{correction.problem}</p>

      <div className="mb-4 space-y-2">
        {originalDisplay.mode !== 'omit' && originalDisplay.mode !== 'insertion' && originalDisplay.text && (
          <div className="diff-removed">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-red-800 dark:text-red-300/80">
              {originalDisplay.label}
            </p>
            <p className="diff-removed-text">{originalDisplay.text}</p>
          </div>
        )}
        {originalDisplay.mode === 'insertion' && (
          <p className="text-xs font-medium text-content-muted">{originalDisplay.label}</p>
        )}
        <div className="diff-added">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-green-800 dark:text-green-300/80">
            Sugerido
          </p>
          <p className="diff-added-text">{correction.suggested_text}</p>
        </div>
      </div>

      {needsAdjust && (
        <p className="mb-3 flex items-start gap-1.5 rounded-lg border border-amber-700/40 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-950 dark:border-amber-500/30 dark:bg-amber-500/10 dark:font-normal dark:text-amber-200">
          <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-800 dark:text-amber-200" aria-hidden />
          <span>Texto com campos a preencher — use Ajustar antes de aprovar.</span>
        </p>
      )}

      {onReviewUpdated && (
        <CorrectionReviewActions
          correction={correction}
          onReviewUpdated={onReviewUpdated}
          preferAdjust={needsAdjust}
        />
      )}

      {canCopyPara && (
        <div className="mb-3">
          <button
            type="button"
            onClick={() => copy(correction.suggested_text, `para_${correction.id}`)}
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-green-700/30 bg-green-100 px-3 py-2.5 text-sm font-medium text-green-900 outline-none transition-colors hover:bg-green-200 focus-visible:ring-2 focus-visible:ring-green-500/60 dark:border-green-500/40 dark:bg-green-500/15 dark:text-green-200 dark:hover:bg-green-500/25 sm:w-auto"
          >
            {isCopied(`para_${correction.id}`) ? (
              <>
                <Check className="h-4 w-4 text-green-400" aria-hidden />
                Texto copiado
              </>
            ) : (
              <>
                <ClipboardCopy className="h-4 w-4" aria-hidden />
                Copiar para o SEI
              </>
            )}
          </button>
        </div>
      )}

      <div className="relative rounded-lg border border-line-subtle bg-canvas/40">
        <button
          type="button"
          onClick={() => setFundOpen((v) => !v)}
          className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-accent-500/60"
          aria-expanded={fundOpen}
        >
          <span className="text-xs font-semibold uppercase tracking-wider text-content-subtle">
            Ver fundamentação jurídica
          </span>
          <ChevronDown
            className={cn(
              'h-4 w-4 shrink-0 text-content-subtle transition-transform',
              fundOpen && 'rotate-180',
            )}
            aria-hidden
          />
        </button>
        {fundOpen && (
          <div className="border-t border-line-subtle px-3 pb-3 pt-2">
            <p className="text-sm text-content-muted">{correction.justification}</p>
            {correction.legal_basis && (
              <p className="tnum mt-2 font-mono text-xs text-accent-400">{correction.legal_basis}</p>
            )}
            {correction.risk && (
              <div className="mt-3 flex items-start gap-2">
                <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-800 dark:text-yellow-400" aria-hidden />
                <p className="text-xs text-amber-950/90 dark:text-yellow-400/70">{correction.risk}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
