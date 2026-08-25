'use client';

import type { DocumentItemResponse, CorrectionResponse } from '@/types';
import { useCopy } from '@/lib/useCopy';
import { Check, ClipboardCopy, CheckCircle2, Lightbulb } from 'lucide-react';
import CorrectionCard from '@/components/analysis/CorrectionCard';

interface ItemDetailProps {
  item: DocumentItemResponse;
  corrections: CorrectionResponse[];
  getUpdatedItemText: (item: DocumentItemResponse, corrections: CorrectionResponse[]) => string;
  showCorrections?: boolean;
}

/**
 * Detalhe do item selecionado: conteúdo original, cópia do item corrigido (SEI) e correções DE → PARA.
 */
export default function ItemDetail({
  item,
  corrections,
  getUpdatedItemText,
  showCorrections = true,
}: ItemDetailProps) {
  const { copy, isCopied } = useCopy();
  const showCopyItem = showCorrections && corrections.length > 0;

  return (
    <div className="col-span-12 space-y-4 lg:col-span-8">
      {/* Conteúdo do item */}
      <div className="glass-card p-5 sm:p-6">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <span className="tnum font-mono text-sm font-semibold text-accent-400">{item.item_number}</span>
          {item.title && (
            <h2 className="text-lg font-semibold tracking-tight text-content-primary">{item.title}</h2>
          )}
          <span className="badge badge-info ml-auto text-[10px]">{item.item_type}</span>
        </div>

        <div className="mb-4 max-h-48 overflow-y-auto rounded-lg border border-line-subtle bg-canvas/60 p-4">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-content-secondary">{item.content}</p>
        </div>

        {showCopyItem && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line-subtle pt-3">
            <span className="flex items-center gap-1.5 text-xs text-content-muted">
              <Lightbulb className="h-3.5 w-3.5 text-accent-400" aria-hidden />
              Copie o item completo pronto para o SEI (com correções aplicadas):
            </span>
            <button
              onClick={() => copy(getUpdatedItemText(item, corrections), `item_full_${item.id}`)}
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
                  Copiar Item Inteiro para o SEI
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Correções do item */}
      {showCorrections &&
        (corrections.length === 0 ? (
          <div className="glass-card p-6 text-center">
            <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-green-400" strokeWidth={1.5} aria-hidden />
            <p className="text-sm font-medium text-green-400">Item adequado</p>
            <p className="mt-1 text-xs text-content-subtle">
              Nenhuma correção necessária. Não é preciso alterar este item no SEI.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {corrections.map((correction, idx) => (
              <CorrectionCard key={correction.id} correction={correction} index={idx} />
            ))}
          </div>
        ))}
    </div>
  );
}
