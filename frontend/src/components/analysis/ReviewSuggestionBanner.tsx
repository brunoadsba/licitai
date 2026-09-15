'use client';

import { CheckCheck, Lightbulb, ShieldAlert, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import type { ReviewSuggestion } from '@/types/reviewer';

interface Props {
  suggestion: ReviewSuggestion | null;
  loading?: boolean;
  onAccept: () => void;
  accepting?: boolean;
  disabled?: boolean;
}

/** Banner consultivo do revisor-assistente — 1 clique para aceitar, nunca auto-aprova. */
export default function ReviewSuggestionBanner({
  suggestion,
  loading,
  onAccept,
  accepting,
  disabled,
}: Props) {
  if (loading) {
    return (
      <div className="rounded-lg border border-line-subtle bg-canvas/40 p-3 text-xs text-content-muted">
        Analisando sugestão do revisor…
      </div>
    );
  }
  if (!suggestion) return null;

  const pct = Math.round(suggestion.confidence * 100);
  const isHigh = suggestion.confidence >= 0.80;
  const isLow = suggestion.confidence < 0.62;

  const label: Record<string, string> = {
    aprovar: 'Sugestão: aprovar',
    rejeitar: 'Sugestão: rejeitar',
    ajustar: 'Sugestão: ajustar',
  };

  const tone = suggestion.suggestion === 'rejeitar' ? 'critical' : suggestion.suggestion === 'ajustar' ? 'medium' : 'low';

  return (
    <div
      className={`rounded-lg border p-3 ${isLow ? 'border-amber-700/40 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-500/10' : 'border-line-subtle bg-canvas/40'}`}
      data-testid="review-suggestion"
      data-suggestion={suggestion.suggestion}
      data-confidence={pct}
    >
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Badge tone={tone as never}>{label[suggestion.suggestion] ?? suggestion.suggestion}</Badge>
        <span className="text-xs font-medium text-content-secondary">{pct}% confiança</span>
        {suggestion.fail_closed && (
          <span className="inline-flex items-center gap-1 text-xs text-amber-800 dark:text-amber-200">
            <ShieldAlert className="h-3.5 w-3.5" aria-hidden />
            fail-closed
          </span>
        )}
        {suggestion.has_placeholder && (
          <span className="inline-flex items-center gap-1 text-xs text-amber-800 dark:text-amber-200">
            <TriangleAlert className="h-3.5 w-3.5" aria-hidden />
            placeholders
          </span>
        )}
      </div>

      <p className="flex gap-1.5 text-xs leading-relaxed text-content-secondary">
        <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-content-muted" aria-hidden />
        <span>{suggestion.reason}</span>
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={isHigh ? 'primary' : 'secondary'}
          onClick={onAccept}
          disabled={!!disabled || !!accepting}
          loading={!!accepting}
          data-testid="accept-suggestion"
          title="Aplica a sugestão (aprovar/rejeitar/ajustar) — você pode desfazer"
        >
          <CheckCheck className="h-3.5 w-3.5" aria-hidden />
          Aceitar sugestão
        </Button>
        <span className="self-center text-xs text-content-muted">
          Você decide — nada vai para o SEI sem sua aprovação.
        </span>
      </div>
    </div>
  );
}
