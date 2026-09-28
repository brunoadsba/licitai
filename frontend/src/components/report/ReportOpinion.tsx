'use client';

import { Check, ClipboardCopy, FileText } from 'lucide-react';
import { useCopy } from '@/lib/useCopy';

/** Parecer final. A cópia não substitui o pacote SEI. */
export default function ReportOpinion({
  opinion,
  analyzedItems,
  totalItems,
}: {
  opinion: string;
  analyzedItems?: number | null;
  totalItems?: number | null;
}) {
  const { copy, isCopied } = useCopy();
  const partial =
    analyzedItems != null &&
    totalItems != null &&
    totalItems > 0 &&
    analyzedItems < totalItems;
  const caveat = partial
    ? `[Este parecer cobre ${analyzedItems.toLocaleString('pt-BR')} de ${totalItems.toLocaleString('pt-BR')} itens verificados — não representa o documento inteiro]\n\n`
    : '';
  return (
    <div className="rounded-lg border border-line-subtle bg-surface/40 border-accent-500/20 p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold tracking-tight text-content-primary">
          <FileText className="h-5 w-5 text-accent-400" aria-hidden />
          Parecer Final
        </h2>
        <button
          onClick={() => copy(`${caveat}${opinion || ''}`, 'final_opinion')}
          className="inline-flex items-center gap-1.5 rounded-lg border border-accent-500/30 bg-accent-500/15 px-3 py-1.5 text-xs font-medium text-accent-400 outline-none transition-colors hover:bg-accent-500/25 focus-visible:ring-2 focus-visible:ring-accent-500/60"
        >
          {isCopied('final_opinion') ? (
            <>
              <Check className="h-3.5 w-3.5 text-green-400" aria-hidden />
              Parecer Copiado!
            </>
          ) : (
            <>
              <ClipboardCopy className="h-3.5 w-3.5" aria-hidden />
              Copiar parecer
            </>
          )}
        </button>
      </div>
      {partial && (
        <p className="mb-3 rounded-md border border-amber-700/40 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-950 [break-inside:avoid] dark:border-amber-500/40 dark:bg-amber-500/10 dark:font-normal dark:text-amber-200">
          Este parecer cobre {analyzedItems?.toLocaleString('pt-BR')} de {totalItems?.toLocaleString('pt-BR')} itens — o trecho
          copiado não representa o documento inteiro.
        </p>
      )}
      <p className="mb-3 text-xs text-content-muted">
        Este parecer não é o pacote SEI e inclui achados ainda não aprovados.
      </p>
      <p className="whitespace-pre-wrap leading-relaxed text-content-secondary">{opinion}</p>
    </div>
  );
}
