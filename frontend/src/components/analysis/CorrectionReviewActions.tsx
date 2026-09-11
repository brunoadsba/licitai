'use client';

import { useState } from 'react';
import { toast } from 'sonner';
import type { CorrectionResponse, ReviewStatus } from '@/types';
import { updateCorrectionReview } from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import { Button } from '@/components/ui/Button';
import { CheckCheck, Pencil, X } from 'lucide-react';

interface CorrectionReviewActionsProps {
  correction: CorrectionResponse;
  onReviewUpdated: (correction: CorrectionResponse) => void;
}

/**
 * Ações humanas de revisão SEI: Aprovar / Rejeitar / Ajustar.
 */
export default function CorrectionReviewActions({
  correction,
  onReviewUpdated,
}: CorrectionReviewActionsProps) {
  const reviewStatus = correction.review_status ?? 'pendente';
  const [saving, setSaving] = useState(false);
  const [adjusting, setAdjusting] = useState(false);
  const [adjustedText, setAdjustedText] = useState(correction.suggested_text);
  const [adjustNote, setAdjustNote] = useState(correction.review_note ?? '');

  async function applyReview(
    status: ReviewStatus,
    extras?: { suggested_text?: string; review_note?: string },
  ) {
    try {
      setSaving(true);
      const updated = await updateCorrectionReview(correction.id, {
        review_status: status,
        review_note: extras?.review_note,
        suggested_text: extras?.suggested_text,
      });
      onReviewUpdated(updated);
      setAdjusting(false);
      const labels: Record<ReviewStatus, string> = {
        aprovada: 'Correção aprovada — cópia SEI liberada',
        rejeitada: 'Correção rejeitada',
        ajustada: 'Correção ajustada — cópia SEI liberada',
        pendente: 'Revisão marcada como pendente',
      };
      toast.success(labels[status]);
    } catch (err) {
      toast.error(getErrorMessage(err, 'analysis').message);
    } finally {
      setSaving(false);
    }
  }

  async function handleAdjustSubmit() {
    const text = adjustedText.trim();
    if (!text) {
      toast.error('Informe o texto corrigido ajustado.');
      return;
    }
    await applyReview('ajustada', {
      suggested_text: text,
      review_note: adjustNote.trim() || undefined,
    });
  }

  return (
    <div className="mb-4 rounded-lg border border-line-subtle bg-canvas/30 p-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-content-subtle">
        Sua decisão
      </p>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          disabled={saving || reviewStatus === 'aprovada'}
          onClick={() => applyReview('aprovada')}
        >
          <CheckCheck className="h-3.5 w-3.5" aria-hidden />
          Aprovar
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={saving || reviewStatus === 'rejeitada'}
          onClick={() => applyReview('rejeitada', { review_note: 'Rejeitada pelo revisor' })}
        >
          <X className="h-3.5 w-3.5" aria-hidden />
          Rejeitar
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={saving}
          onClick={() => {
            setAdjustedText(correction.suggested_text);
            setAdjustNote(correction.review_note ?? '');
            setAdjusting((v) => !v);
          }}
        >
          <Pencil className="h-3.5 w-3.5" aria-hidden />
          Ajustar
        </Button>
      </div>

      {adjusting && (
        <div className="mt-3 space-y-2">
          <label className="block text-xs text-content-muted" htmlFor={`adj-${correction.id}`}>
            Texto sugerido (ajustado)
          </label>
          <textarea
            id={`adj-${correction.id}`}
            value={adjustedText}
            onChange={(e) => setAdjustedText(e.target.value)}
            rows={4}
            className="w-full rounded-lg border border-line-subtle bg-canvas/60 px-3 py-2 text-sm text-content-primary outline-none focus-visible:ring-2 focus-visible:ring-accent-500/60"
          />
          <label className="block text-xs text-content-muted" htmlFor={`note-${correction.id}`}>
            Nota (opcional)
          </label>
          <input
            id={`note-${correction.id}`}
            value={adjustNote}
            onChange={(e) => setAdjustNote(e.target.value)}
            className="w-full rounded-lg border border-line-subtle bg-canvas/60 px-3 py-2 text-sm text-content-primary outline-none focus-visible:ring-2 focus-visible:ring-accent-500/60"
          />
          <div className="flex gap-2">
            <Button size="sm" disabled={saving} onClick={handleAdjustSubmit}>
              Salvar ajuste
            </Button>
            <Button size="sm" variant="ghost" disabled={saving} onClick={() => setAdjusting(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      )}

      {correction.review_note && (
        <p className="mt-2 text-xs text-content-muted">Nota: {correction.review_note}</p>
      )}
    </div>
  );
}
