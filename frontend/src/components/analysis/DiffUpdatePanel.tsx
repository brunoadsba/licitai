'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { GitCompareArrows } from 'lucide-react';
import { diffDocuments, extractErrorMessage } from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import type { Tone } from '@/components/ui/Badge';
import type { DiffItemResponse } from '@/types';

function statusTone(status: string): Tone {
  switch (status) {
    case 'alterado':
      return 'medium';
    case 'adicionado':
      return 'low';
    case 'removido':
      return 'critical';
    default:
      return 'neutral';
  }
}

interface DiffUpdatePanelProps {
  oldDocumentId: string;
  newDocumentId: string;
  onPickItemNumber?: (itemNumber: string) => void;
}

/** Painel lateral: diff da republicação/aditivo (alterado|adicionado|removido). */
export default function DiffUpdatePanel({
  oldDocumentId,
  newDocumentId,
  onPickItemNumber,
}: DiffUpdatePanelProps) {
  const [items, setItems] = useState<DiffItemResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const result = await diffDocuments(oldDocumentId, newDocumentId);
        if (cancelled) return;
        const changed = (result.itens || []).filter((i) =>
          ['alterado', 'adicionado', 'removido'].includes(i.status),
        );
        setItems(changed);
        setError(null);
      } catch (err) {
        if (!cancelled) {
          setError(extractErrorMessage(err, 'Não foi possível carregar o diff.'));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [oldDocumentId, newDocumentId]);

  return (
    <aside className="glass-card col-span-12 space-y-3 p-4 lg:col-span-3">
      <div className="flex items-start gap-2">
        <GitCompareArrows className="mt-0.5 h-4 w-4 shrink-0 text-accent-400" aria-hidden />
        <div>
          <p className="text-sm font-medium text-content-primary">Atualização de TR</p>
          <p className="text-xs text-content-muted">
            Itens alterados/adicionados/removidos vs. versão anterior.
          </p>
        </div>
      </div>

      <Link
        href={`/comparacao/versoes`}
        className="text-xs text-accent-400 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-accent-500/60"
      >
        Abrir comparação completa
      </Link>

      {loading && <p className="text-xs text-content-subtle">Carregando diff…</p>}
      {error && <p className="text-xs text-red-400">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="text-xs text-content-subtle">Nenhuma diferença relevante.</p>
      )}

      <ul className="max-h-64 space-y-2 overflow-y-auto lg:max-h-[calc(100dvh-360px)]">
        {items.map((item) => (
          <li key={`${item.status}-${item.item_number}-${item.titulo || ''}`}>
            <button
              type="button"
              className="w-full rounded-lg border border-line-subtle bg-white/[0.02] p-2.5 text-left outline-none transition-colors hover:bg-white/[0.04] focus-visible:ring-2 focus-visible:ring-accent-500/60"
              onClick={() => {
                if (item.item_number && onPickItemNumber) {
                  onPickItemNumber(item.item_number);
                }
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="tnum text-xs font-medium text-content-primary">
                  {item.item_number || '—'}
                </span>
                <Badge tone={statusTone(item.status)}>{item.status}</Badge>
              </div>
              {item.titulo && (
                <p className="mt-1 line-clamp-2 text-[11px] text-content-muted">{item.titulo}</p>
              )}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
