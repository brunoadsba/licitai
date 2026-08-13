import type { DocumentItemResponse, CorrectionResponse } from '@/types';
import { getSeverityBadge } from '@/lib/badges';

const SEVERITY_ORDER = ['info', 'baixo', 'medio', 'alto', 'critico'];

interface ItemListProps {
  items: DocumentItemResponse[];
  selectedId: string | null;
  getCorrections: (itemId: string) => CorrectionResponse[];
  onSelect: (item: DocumentItemResponse) => void;
}

/**
 * Lista lateral de itens do documento com badge de severidade máxima.
 */
export default function ItemList({ items, selectedId, getCorrections, onSelect }: ItemListProps) {
  return (
    <div className="col-span-4 space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto pr-2">
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
            className={`w-full text-left p-4 rounded-xl transition-all duration-200 ${
              isActive
                ? 'bg-primary-500/10 border border-primary-500/30'
                : 'glass-card-interactive'
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <span className="text-xs text-primary-400 font-mono">
                  {item.item_number}
                </span>
                {item.title && (
                  <p className="text-sm text-gray-200 font-medium truncate mt-0.5">
                    {item.title}
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  {item.item_type} • pág. {item.page_number || '—'}
                </p>
              </div>

              {hasIssues && (
                <span className={`badge ${getSeverityBadge(maxSeverity)} text-[10px]`}>
                  {corrections.length}
                </span>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
