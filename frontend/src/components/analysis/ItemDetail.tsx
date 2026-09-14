'use client';

import type { DocumentItemResponse, CorrectionResponse } from '@/types';
import { useCopy } from '@/lib/useCopy';
import { Check, ClipboardCopy, CheckCircle2, Lightbulb, ListTree, CircleDashed } from 'lucide-react';
import CorrectionCard, { isSeiCopyAllowed } from '@/components/analysis/CorrectionCard';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

interface ItemDetailProps {
  item: DocumentItemResponse;
  corrections: CorrectionResponse[];
  getUpdatedItemText: (item: DocumentItemResponse, corrections: CorrectionResponse[]) => string;
  showCorrections?: boolean;
  onReviewUpdated?: (correction: CorrectionResponse) => void;
  /** IDs dos itens efetivamente analisados pela LLM nesta rodada */
  analyzedItemIds?: string[] | null;
  analysisDone?: boolean;
  className?: string;
}

type EmptyStateKind = 'heading' | 'not_analyzed' | 'ok';

function resolveEmptyState(
  item: DocumentItemResponse,
  analyzedItemIds: string[] | null | undefined,
  analysisDone: boolean,
): EmptyStateKind {
  if (item.is_substantive === false) {
    return 'heading';
  }

  if (item.is_substantive === undefined) {
    const bodyHint = item.content.trim();
    const looksLikeHeading =
      bodyHint.length < 60 && !/[.;:]/.test(bodyHint.slice((item.title?.length ?? 0) + 5));
    if (looksLikeHeading) {
      return 'heading';
    }
  }

  if (analysisDone && analyzedItemIds && analyzedItemIds.length > 0) {
    if (!analyzedItemIds.includes(item.id)) {
      return 'not_analyzed';
    }
  }

  return 'ok';
}

/**
 * Detalhe do item selecionado: conteúdo original, cópia do item corrigido (SEI) e correções DE → PARA.
 */
export default function ItemDetail({
  item,
  corrections,
  getUpdatedItemText,
  showCorrections = true,
  onReviewUpdated,
  analyzedItemIds,
  analysisDone = false,
  className,
}: ItemDetailProps) {
  const { copy, isCopied } = useCopy();
  const seiCorrections = corrections.filter((c) => isSeiCopyAllowed(c.review_status));
  const showCopyItem = showCorrections && seiCorrections.length > 0;
  const emptyKind = resolveEmptyState(item, analyzedItemIds, analysisDone);

  return (
    <div className={cn('col-span-12 space-y-4 lg:col-span-8', className)}>
      {/* Conteúdo do item */}
      <div className="rounded-lg border border-line-subtle bg-surface/50 p-5 sm:p-6">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <span className="tnum font-mono text-sm font-semibold text-accent-400">{item.item_number}</span>
          {item.title && (
            <h2 className="text-lg font-semibold tracking-tight text-content-primary">{item.title}</h2>
          )}
          {emptyKind === 'heading' ? (
            <Badge tone="neutral" className="ml-auto text-[10px]">
              Tópico
            </Badge>
          ) : (
            <Badge tone="neutral" className="ml-auto text-[10px]">
              Cláusula
            </Badge>
          )}
        </div>

        <div className="mb-4 max-h-48 overflow-y-auto rounded-lg border border-line-subtle bg-canvas/60 p-4">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-content-secondary">{item.content}</p>
        </div>

        {showCorrections && corrections.length > 0 && !showCopyItem && (
          <div className="border-t border-line-subtle pt-3">
            <span className="flex items-center gap-1.5 text-xs text-content-muted">
              <Lightbulb className="h-3.5 w-3.5 text-content-muted" aria-hidden />
              Cópia do item para o SEI disponível somente com correções aprovadas ou ajustadas.
            </span>
          </div>
        )}

        {showCopyItem && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line-subtle pt-3">
            <span className="flex items-center gap-1.5 text-xs text-content-muted">
              <Lightbulb className="h-3.5 w-3.5 text-accent-400" aria-hidden />
              Copie o item com correções aprovadas/ajustadas aplicadas (SEI):
            </span>
            <button
              type="button"
              onClick={() => copy(getUpdatedItemText(item, seiCorrections), `item_full_${item.id}`)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-accent-500/30 bg-accent-500/15 px-3 py-1.5 text-xs font-medium text-accent-400 transition-colors outline-none hover:bg-accent-500/25 focus-visible:ring-2 focus-visible:ring-accent-500/60"
            >
              {isCopied(`item_full_${item.id}`) ? (
                <>
                  <Check className="h-3.5 w-3.5 text-green-400" aria-hidden />
                  Copiado!
                </>
              ) : (
                <>
                  <ClipboardCopy className="h-3.5 w-3.5" aria-hidden />
                  Copiar item para o SEI
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Correções do item */}
      {showCorrections &&
        (corrections.length === 0 ? (
          <EmptyItemState kind={emptyKind} />
        ) : (
          <div className="space-y-3">
            {corrections.map((correction, idx) => (
              <CorrectionCard
                key={correction.id}
                correction={correction}
                index={idx}
                onReviewUpdated={onReviewUpdated}
              />
            ))}
          </div>
        ))}
    </div>
  );
}

function EmptyItemState({ kind }: { kind: EmptyStateKind }) {
  if (kind === 'heading') {
    return (
      <div className="rounded-lg border border-line-subtle bg-surface/40 p-6 text-center">
        <ListTree className="mx-auto mb-3 h-10 w-10 text-content-subtle" strokeWidth={1.5} aria-hidden />
        <p className="text-sm font-medium text-content-primary">Tópico de organização do documento</p>
        <p className="mt-1 text-xs text-content-subtle">
          Este item organiza a hierarquia do TR. As análises técnicas e jurídicas são realizadas
          sobre os subitens e cláusulas de conteúdo.
        </p>
      </div>
    );
  }

  if (kind === 'not_analyzed') {
    return (
      <div className="rounded-lg border border-line-subtle bg-surface/40 p-6 text-center">
        <CircleDashed className="mx-auto mb-3 h-10 w-10 text-amber-500/80" strokeWidth={1.5} aria-hidden />
        <p className="text-sm font-medium text-content-primary">Item não analisado nesta rodada</p>
        <p className="mt-1 text-xs text-content-subtle">
          A análise priorizou as cláusulas mais críticas. Para analisar este item, use
          &quot;Reanalisar faltantes&quot;.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-line-subtle bg-surface/40 p-6 text-center">
      <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-green-400" strokeWidth={1.5} aria-hidden />
      <p className="text-sm font-medium text-green-400">Nenhuma inconformidade encontrada</p>
      <p className="mt-1 text-xs text-content-subtle">
        O texto desta cláusula foi analisado e não apresentou problemas jurídicos ou estruturais.
      </p>
    </div>
  );
}
