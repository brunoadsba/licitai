import type { CorrectionResponse, DocumentItemResponse } from '@/types';

const SEVERITY_ORDER = ['info', 'baixo', 'medio', 'alto', 'critico'];

export type PriorityMode = 'priority' | 'all';

/** Correção prioritária: severidade alto/crítico OU categoria estrutural (Art. 6). */
export function isPriorityCorrection(c: CorrectionResponse): boolean {
  const sev = SEVERITY_ORDER.indexOf(c.severity);
  if (sev >= SEVERITY_ORDER.indexOf('alto')) return true;
  if (c.category === 'estrutural') return true;
  return false;
}

export function filterPriorityCorrections(
  corrections: CorrectionResponse[],
  mode: PriorityMode,
): CorrectionResponse[] {
  if (mode === 'all') return corrections;
  return corrections.filter(isPriorityCorrection);
}

export function countPendingPriority(corrections: CorrectionResponse[]): number {
  return corrections.filter(
    (c) => isPriorityCorrection(c) && (c.review_status ?? 'pendente') === 'pendente',
  ).length;
}

export function itemHasVisibleCorrections(
  itemId: string,
  corrections: CorrectionResponse[],
  mode: PriorityMode,
): boolean {
  return filterPriorityCorrections(
    corrections.filter((c) => c.document_item_id === itemId),
    mode,
  ).length > 0;
}

export function filterItemsForPriorityMode(
  items: DocumentItemResponse[],
  corrections: CorrectionResponse[],
  mode: PriorityMode,
): DocumentItemResponse[] {
  if (mode === 'all') return items;
  const withPriority = items.filter((item) =>
    itemHasVisibleCorrections(item.id, corrections, 'priority'),
  );
  return withPriority.length > 0 ? withPriority : items;
}
