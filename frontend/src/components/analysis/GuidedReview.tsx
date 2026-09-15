'use client';

import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, ChevronLeft, ChevronRight, ListTree } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import CorrectionCard from '@/components/analysis/CorrectionCard';
import ReviewSuggestionBanner from '@/components/analysis/ReviewSuggestionBanner';
import { getReviewSuggestion, updateCorrectionReview } from '@/lib/api';
import type { CorrectionResponse } from '@/types';
import type { ReviewSuggestion } from '@/types/reviewer';
import { filterPriorityCorrections } from '@/lib/priorityQueue';

const SEVERITY_ORDER = ['critico', 'alto', 'estrutural'] as const;

function severityRank(c: CorrectionResponse): number {
  if (c.category === 'estrutural') return 0;
  const idx = SEVERITY_ORDER.indexOf(c.severity as typeof SEVERITY_ORDER[number]);
  return idx === -1 ? 99 : idx;
}

interface GuidedReviewProps {
  corrections: CorrectionResponse[];
  analysisId: string;
  onReviewUpdated: (c: CorrectionResponse) => void;
  onExit: () => void;
  onAfterComplete?: () => void;
}

/** Passo-a-passo 1-por-vez sobre as pendências prioritárias — reúso puro de `CorrectionCard`. */
export default function GuidedReview({
  corrections,
  analysisId,
  onReviewUpdated,
  onExit,
  onAfterComplete,
}: GuidedReviewProps) {
  const pending = useMemo(() => {
    const base = filterPriorityCorrections(corrections, 'priority').filter(
      (c) => (c.review_status ?? 'pendente') === 'pendente'
    );
    return [...base].sort((a, b) => severityRank(a) - severityRank(b));
  }, [corrections]);

  const total = pending.length;
  const [idx, setIdx] = useState(0);
  const [suggestion, setSuggestion] = useState<ReviewSuggestion | null>(null);
  const [sugLoading, setSugLoading] = useState(false);
  const [accepting, setAccepting] = useState(false);

  const current = total > 0 ? pending[Math.min(idx, total - 1)] : null;
  const pct = total === 0 ? 100 : Math.round(((total - pending.length + idx + 1) / total) * 100);

  useEffect(() => {
    if (idx >= total && total > 0) setIdx(total - 1);
    if (total === 0) setIdx(0);
  }, [idx, total]);

  useEffect(() => {
    if (!current || !analysisId) {
      setSuggestion(null);
      return;
    }
    let cancelled = false;
    setSugLoading(true);
    getReviewSuggestion(analysisId, current.id)
      .then((s) => {
        if (!cancelled) setSuggestion(s);
      })
      .catch(() => {
        if (!cancelled) setSuggestion(null);
      })
      .finally(() => {
        if (!cancelled) setSugLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [current?.id, analysisId]);

  function handleUpdated(next: CorrectionResponse) {
    onReviewUpdated(next);
    // Avança para a próxima pendência real após o estado propagar (próximo render recalcula pending).
    // Se era a última, o efeito acima ajusta o índice; se acabou, mostra conclusão.
  }

  async function handleAcceptSuggestion() {
    if (!current || !suggestion) return;
    const kind = suggestion.suggestion;
    if (kind === 'ajustar' && suggestion.has_placeholder) {
      return;
    }
    try {
      setAccepting(true);
      const status = kind === 'aprovar' ? 'aprovada' : kind === 'rejeitar' ? 'rejeitada' : 'ajustada';
      const updated = await updateCorrectionReview(current.id, { review_status: status as never });
      onReviewUpdated(updated);
    } finally {
      setAccepting(false);
    }
  }

  function goNext() {
    setIdx((v) => Math.min(v + 1, total - 1));
  }
  function goPrev() {
    setIdx((v) => Math.max(v - 1, 0));
  }

  if (total === 0) {
    const hasAnyPriority = filterPriorityCorrections(corrections, 'priority').length > 0;
    return (
      <div className="rounded-lg border border-line-subtle bg-surface/30 p-8 text-center">
        <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-green-400" aria-hidden />
        <p className="text-sm font-medium text-content-primary">
          {hasAnyPriority ? 'Todas as pendências prioritárias foram revisadas' : 'Nenhuma pendência prioritária'}
        </p>
        <p className="mx-auto mt-1 max-w-md text-xs text-content-subtle">
          {hasAnyPriority
            ? 'Use "Copiar pacote SEI" no topo para levar as aprovadas ao SEI, ou "Ver todas" para revisar o restante.'
            : 'Este TR não tem achados alto/crítico ou estruturais pendentes. Veja "Ver todas" para o restante ou siga para o relatório.'}
        </p>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <Button size="sm" variant="secondary" onClick={onExit} data-testid="guided-exit">
            Ver todas
          </Button>
          {hasAnyPriority && onAfterComplete && (
            <Button size="sm" onClick={onAfterComplete}>
              Ir ao pacote SEI
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="guided-review">
      <div className="rounded-lg border border-line-subtle bg-surface/40 p-4">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-content-subtle">
            Revisão guiada · {idx + 1} de {total}
          </p>
          <Button size="sm" variant="ghost" onClick={onExit} data-testid="guided-exit">
            <ListTree className="h-3.5 w-3.5" aria-hidden />
            Sair do guiado
          </Button>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-canvas">
          <div
            className="h-full rounded-full bg-accent-500 transition-all"
            style={{ width: `${Math.max(6, pct)}%` }}
            aria-hidden
          />
        </div>
        <p className="mt-2 text-xs text-content-muted">
          Revise uma por vez. Aprovar/rejeitar/ajustar aqui já atualiza nota e risco; o próximo aparece sozinho.
        </p>
      </div>

      {current && (
        <>
          <ReviewSuggestionBanner
            suggestion={suggestion}
            loading={sugLoading}
            onAccept={handleAcceptSuggestion}
            accepting={accepting}
            disabled={suggestion?.suggestion === 'ajustar' && !!suggestion?.has_placeholder}
          />
          <CorrectionCard
            key={current.id}
            correction={current}
            index={0}
            onReviewUpdated={handleUpdated}
          />
        </>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button size="sm" variant="secondary" onClick={goPrev} disabled={idx === 0} data-testid="guided-prev">
          <ChevronLeft className="h-4 w-4" aria-hidden />
          Anterior
        </Button>
        <span className="text-xs text-content-muted">
          {idx + 1} / {total} · use as setas para navegar
        </span>
        <Button size="sm" variant="secondary" onClick={goNext} disabled={idx >= total - 1} data-testid="guided-next">
          Próxima
          <ChevronRight className="h-4 w-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
