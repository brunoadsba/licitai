'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle2, ChevronLeft, ChevronRight, ListTree, Undo2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import CorrectionCard from '@/components/analysis/CorrectionCard';
import ReviewSuggestionBanner from '@/components/analysis/ReviewSuggestionBanner';
import { getReviewSuggestion, trackSuggestion, updateCorrectionReview } from '@/lib/api';
import type { CorrectionResponse } from '@/types';
import type { ReviewSuggestion } from '@/types/reviewer';
import { filterPriorityCorrections } from '@/lib/priorityQueue';
import { copy } from '@/lib/copy';

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

  const storageKey = `licitai-review-${analysisId}`;
  function readResumeId(): string | null {
    try {
      return window.localStorage.getItem(storageKey);
    } catch {
      return null;
    }
  }
  function writeResumeId(id: string) {
    try {
      window.localStorage.setItem(storageKey, id);
    } catch {
      /* storage indisponível: segue sem retomada */
    }
  }

  const reviewedCount = filterPriorityCorrections(corrections, 'priority').filter(
    (c) => (c.review_status ?? 'pendente') !== 'pendente',
  ).length;
  const reviewableTotal = filterPriorityCorrections(corrections, 'priority').length;
  const [suggestion, setSuggestion] = useState<ReviewSuggestion | null>(null);
  const [sugLoading, setSugLoading] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [showKeys, setShowKeys] = useState(false);
  const [liveMsg, setLiveMsg] = useState('');
  const [lastUndo, setLastUndo] = useState<{
    id: string;
    status: string;
    text: string;
    note: string;
  } | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  const current = total > 0 ? pending[Math.min(idx, total - 1)] : null;

  const resumed = useRef(false);
  useEffect(() => {
    resumed.current = false;
  }, [analysisId]);
  useEffect(() => {
    if (resumed.current || total === 0) return;
    resumed.current = true;
    const resumeId = readResumeId();
    if (resumeId) {
      const pos = pending.findIndex((c) => c.id === resumeId);
      if (pos > 0) setIdx(pos);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [total]);

  useEffect(() => {
    if (current) writeResumeId(current.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id]);

  function restartFromTop() {
    writeResumeId('');
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      /* sem storage: só volta ao topo */
    }
    setIdx(0);
  }
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
    const prev = current && current.id === next.id ? current : null;
    onReviewUpdated(next);
    if (prev) {
      setLastUndo({
        id: next.id,
        status: prev.review_status ?? 'pendente',
        text: prev.suggested_text,
        note: prev.review_note ?? '',
      });
    }
    const label =
      next.review_status === 'aprovada'
        ? 'Correção aprovada'
        : next.review_status === 'rejeitada'
          ? 'Correção rejeitada'
          : next.review_status === 'ajustada'
            ? 'Correção ajustada'
            : 'Correção atualizada';
    setLiveMsg(label);
    window.setTimeout(focusCard, 50);
  }

  async function handleUndo() {
    if (!lastUndo) return;
    const snapshot = lastUndo;
    setLastUndo(null);
    try {
      const updated = await updateCorrectionReview(snapshot.id, {
        review_status: snapshot.status as never,
        suggested_text: snapshot.text,
        review_note: snapshot.note || undefined,
      });
      onReviewUpdated(updated);
      setLiveMsg('Decisão desfeita');
    } catch {
      setLastUndo(snapshot);
    }
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
      trackSuggestion(analysisId, current.id, kind, status, suggestion.confidence).catch(() => {});
      handleUpdated(updated);
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

  function clickAction(testid: string) {
    const root = rootRef.current;
    const btn = root?.querySelector<HTMLElement>(`[data-testid="${testid}"]`);
    btn?.click();
    return !!btn;
  }

  function focusCard() {
    const root = rootRef.current;
    const card = root?.querySelector<HTMLElement>('[data-testid="guided-card"]');
    card?.focus({ preventScroll: true });
    card?.scrollIntoView({ block: 'nearest' });
  }

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (window.matchMedia?.('(pointer: coarse)').matches) return;
    function onKey(e: KeyboardEvent) {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t?.closest('input, textarea, select, [contenteditable="true"], [role="dialog"]')) return;
      if (document.querySelector('[role="dialog"]')) return;
      const k = e.key.toLowerCase();
      if (k === 'a') {
        if (clickAction('review-approve')) e.preventDefault();
      } else if (k === 'r') {
        if (clickAction('review-reject')) e.preventDefault();
      } else if (k === 'j') {
        if (clickAction('review-adjust')) {
          e.preventDefault();
          window.setTimeout(() => {
            rootRef.current
              ?.querySelector<HTMLElement>('textarea')
              ?.focus({ preventScroll: true });
          }, 50);
        }
      } else if (k === 'n') {
        e.preventDefault();
        goNext();
        window.setTimeout(focusCard, 50);
      } else if (k === '?') {
        e.preventDefault();
        setShowKeys((v) => !v);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id, total]);

  if (total === 0) {
    const hasAnyPriority = filterPriorityCorrections(corrections, 'priority').length > 0;
    return (
      <div className="rounded-lg border border-line-subtle bg-surface/30 p-8 text-center" data-testid="guided-review">
        <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-green-400" aria-hidden />
        <p className="text-sm font-medium text-content-primary">
          {hasAnyPriority ? copy.analysis.guidedDone : copy.analysis.guidedNone}
        </p>
        <p className="mx-auto mt-1 max-w-md text-xs text-content-subtle">
          {hasAnyPriority ? copy.analysis.guidedDoneHint : copy.analysis.guidedNoneHint}
        </p>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <Button size="sm" variant="secondary" onClick={onExit} data-testid="guided-exit">
            {copy.cta.verTodas}
          </Button>
          {hasAnyPriority && onAfterComplete && (
            <Button size="sm" onClick={onAfterComplete}>
              {copy.analysis.goToSei}
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className="space-y-4"
      data-testid="guided-review"
      ref={rootRef}
      aria-keyshortcuts="a r j n ?"
    >
      <span aria-live="polite" className="sr-only">
        {liveMsg}
      </span>
      <div className="rounded-lg border border-line-subtle bg-surface/40 p-4">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-content-subtle">
            {copy.analysis.guidedLabel(idx + 1, total)} · {reviewedCount} de {reviewableTotal} revisados
          </p>
          <div className="flex items-center gap-1">
            {lastUndo && (
              <Button size="sm" variant="ghost" onClick={handleUndo} data-testid="guided-undo">
                <Undo2 className="h-3.5 w-3.5" aria-hidden />
                Desfazer
              </Button>
            )}
            <Button size="sm" variant="ghost" onClick={restartFromTop} title="Voltar ao primeiro pendente">
              Recomeçar
            </Button>
            <Button size="sm" variant="ghost" onClick={onExit} data-testid="guided-exit">
              <ListTree className="h-3.5 w-3.5" aria-hidden />
              Sair do guiado
            </Button>
          </div>
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
        <div data-testid="guided-card" tabIndex={-1} className="space-y-4 outline-none focus-visible:ring-2 focus-visible:ring-accent-500/60 rounded-lg">
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
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button size="sm" variant="secondary" onClick={goPrev} disabled={idx === 0} data-testid="guided-prev">
          <ChevronLeft className="h-4 w-4" aria-hidden />
          Anterior
        </Button>
        <span className="text-xs text-content-muted">
          {idx + 1} / {total} · use as setas para navegar ·{' '}
          <button
            type="button"
            className="underline"
            onClick={() => setShowKeys((v) => !v)}
            aria-expanded={showKeys}
          >
            atalhos (?)
          </button>
        </span>
        <Button size="sm" variant="secondary" onClick={goNext} disabled={idx >= total - 1} data-testid="guided-next">
          Próxima
          <ChevronRight className="h-4 w-4" aria-hidden />
        </Button>
      </div>
      {showKeys && (
        <p className="text-xs text-content-muted">
          Teclas:{' '}
          <kbd aria-label="tecla A">a</kbd> aprovar ·{' '}
          <kbd aria-label="tecla R">r</kbd> rejeitar ·{' '}
          <kbd aria-label="tecla J">j</kbd> ajustar ·{' '}
          <kbd aria-label="tecla N">n</kbd> próximo ·{' '}
          <kbd aria-label="tecla interrogação">?</kbd> ajuda. Botão Desfazer
          aparece no topo após decidir.
        </p>
      )}
    </div>
  );
}
