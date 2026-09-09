'use client';

import type { CorrectionResponse, ReviewStatus } from '@/types';
import { CATEGORY_LABELS, SEVERITY_LABELS } from '@/types';
import { AGENT_ORIGIN_CONFIG, getCategoryBadge, getSeverityBadge } from '@/lib/badges';
import { useCopy } from '@/lib/useCopy';
import CorrectionReviewActions from '@/components/analysis/CorrectionReviewActions';
import { Check, ClipboardCopy, TriangleAlert } from 'lucide-react';

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

const REVIEW_STATUS_BADGE: Record<ReviewStatus, string> = {
  pendente: 'badge-medio',
  aprovada: 'badge-baixo',
  rejeitada: 'badge-critico',
  ajustada: 'badge-baixo',
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
  const agent = correction.agent_origin ? AGENT_ORIGIN_CONFIG[correction.agent_origin] : null;
  const AgentIcon = agent?.icon;
  const reviewStatus = correction.review_status ?? 'pendente';
  const canCopyPara = isSeiCopyAllowed(reviewStatus);

  return (
    <div
      className="glass-card animate-slide-up p-5"
      style={{ animationDelay: `${Math.min(index, 6) * 50}ms` }}
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {agent && AgentIcon && (
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${agent.badgeClass}`}
            >
              <AgentIcon className="h-3 w-3" aria-hidden />
              {agent.label}
            </span>
          )}
          <span className={`badge ${getCategoryBadge(correction.category)}`}>
            {CATEGORY_LABELS[correction.category] || correction.category}
          </span>
          <span className={`badge ${getSeverityBadge(correction.severity)}`}>
            {SEVERITY_LABELS[correction.severity] || correction.severity}
          </span>
          <span className={`badge ${REVIEW_STATUS_BADGE[reviewStatus]}`}>
            Revisão: {REVIEW_STATUS_LABELS[reviewStatus]}
          </span>
        </div>

        <button
          type="button"
          disabled={!canCopyPara}
          onClick={() => {
            if (!canCopyPara) return;
            copy(correction.suggested_text, `para_${correction.id}`);
          }}
          title={
            canCopyPara
              ? 'Copiar texto de substituição para colar no SEI'
              : 'Disponível apenas para correções aprovadas ou ajustadas'
          }
          className="inline-flex items-center gap-1.5 rounded-lg border border-green-500/40 bg-green-500/15 px-3 py-1.5 text-xs font-medium text-green-300 outline-none transition-colors hover:bg-green-500/25 focus-visible:ring-2 focus-visible:ring-green-500/60 disabled:cursor-not-allowed disabled:border-line-subtle disabled:bg-canvas/40 disabled:text-content-subtle disabled:hover:bg-canvas/40"
        >
          {isCopied(`para_${correction.id}`) ? (
            <>
              <Check className="h-3.5 w-3.5 text-green-400" aria-hidden />
              Texto Copiado!
            </>
          ) : (
            <>
              <ClipboardCopy className="h-3.5 w-3.5" aria-hidden />
              Copiar Texto Corrigido (PARA)
            </>
          )}
        </button>
      </div>

      <p className="mb-4 text-sm text-content-secondary">{correction.problem}</p>

      <div className="mb-4 space-y-2">
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
              onClick={() => {
                if (!canCopyPara) return;
                copy(correction.suggested_text, `para_sub_${correction.id}`);
              }}
              title={
                canCopyPara
                  ? undefined
                  : 'Disponível apenas para correções aprovadas ou ajustadas'
              }
              className="text-[11px] text-green-400/80 underline outline-none hover:text-green-300 focus-visible:ring-2 focus-visible:ring-green-500/60 disabled:cursor-not-allowed disabled:text-content-subtle disabled:no-underline disabled:hover:text-content-subtle"
            >
              {isCopied(`para_sub_${correction.id}`) ? 'Copiado!' : 'Copiar'}
            </button>
          </div>
          <p className="text-sm text-green-300/90">{correction.suggested_text}</p>
        </div>
      </div>

      {onReviewUpdated && (
        <CorrectionReviewActions
          correction={correction}
          onReviewUpdated={onReviewUpdated}
        />
      )}

      <div className="relative rounded-lg border border-line-subtle bg-canvas/40 p-3">
        <div className="mb-1 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-content-subtle">
            Justificativa &amp; Fundamentação
          </p>
          <button
            type="button"
            onClick={() =>
              copy(
                `${correction.justification}${correction.legal_basis ? ` (Fundamento: ${correction.legal_basis})` : ''}`,
                `just_${correction.id}`,
              )
            }
            className="text-[11px] text-accent-400/80 underline outline-none hover:text-accent-300 focus-visible:ring-2 focus-visible:ring-accent-500/60"
          >
            {isCopied(`just_${correction.id}`) ? 'Copiado!' : 'Copiar Justificativa'}
          </button>
        </div>
        <p className="text-sm text-content-muted">{correction.justification}</p>
        {correction.legal_basis && (
          <p className="tnum mt-2 font-mono text-xs text-accent-400">{correction.legal_basis}</p>
        )}
      </div>

      <div className="mt-3 flex items-start gap-2">
        <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-yellow-400" aria-hidden />
        <p className="text-xs text-yellow-400/70">{correction.risk}</p>
      </div>
    </div>
  );
}
