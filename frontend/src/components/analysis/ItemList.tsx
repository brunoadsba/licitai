'use client';

import type { DocumentItemResponse, CorrectionResponse } from '@/types';
import { getSeverityTone } from '@/lib/badges';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

const SEVERITY_ORDER = ['info', 'baixo', 'medio', 'alto', 'critico'];

interface ItemListProps {
  items: DocumentItemResponse[];
  selectedId: string | null;
  getCorrections: (itemId: string) => CorrectionResponse[];
  onSelect: (item: DocumentItemResponse) => void;
  className?: string;
}

/**
 * Lista de itens do documento com badge de severidade máxima.
 * Empilha acima do detalhe no mobile (col-span-12) e vira coluna lateral no desktop.
 */
export default function ItemList({ items, selectedId, getCorrections, onSelect, className }: ItemListProps) {
  return (
    <div
      className={cn(
        'col-span-12 max-h-[320px] space-y-2 overflow-y-auto pr-1 lg:col-span-4 lg:max-h-[calc(100dvh-280px)] lg:pr-2',
        className,
      )}
    >
      {items.map((item) => {
        const corrections = getCorrections(item.id);
        const isActive = selectedId === item.id;
        const hasIssues = corrections.length > 0;
        const maxSeverity = corrections.reduce((max: string, c: CorrectionResponse) => {
          return SEVERITY_ORDER.indexOf(c.severity) > SEVERITY_ORDER.indexOf(max) ? c.severity : max;
        }, 'info');

        return (
          <button
            key={item.id}
            onClick={() => onSelect(item)}
            aria-current={isActive ? 'true' : undefined}
            className={cn(
              'w-full rounded-xl p-4 text-left transition-all duration-150 outline-none',
              'focus-visible:ring-2 focus-visible:ring-accent-500/60',
              isActive
                ? 'border border-accent-500/40 bg-accent-500/10'
                : 'rounded-xl border border-line-subtle bg-surface/40 hover:bg-surface-hover/60',
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <span className="tnum font-mono text-xs text-accent-400">{item.item_number}</span>
                {item.title && (
                  <p className="mt-0.5 truncate text-sm font-medium text-content-primary">{item.title}</p>
                )}
                <p className="tnum mt-1 text-xs text-content-subtle">
                  {item.item_type} · pág. {item.page_number || '—'}
                </p>
              </div>

              {hasIssues && (
                <Badge tone={getSeverityTone(maxSeverity)} className="text-[10px]">
                  {corrections.length}
                </Badge>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
