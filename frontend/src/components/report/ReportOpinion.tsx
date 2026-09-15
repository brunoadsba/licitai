'use client';

import { Check, ClipboardCopy, FileText } from 'lucide-react';
import { useCopy } from '@/lib/useCopy';

/** Parecer final com botão de cópia SEI — extraído de `app/report/[id]/page.tsx`. */
export default function ReportOpinion({ opinion }: { opinion: string }) {
  const { copy, isCopied } = useCopy();
  return (
    <div className="rounded-lg border border-line-subtle bg-surface/40 border-accent-500/20 p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold tracking-tight text-content-primary">
          <FileText className="h-5 w-5 text-accent-400" aria-hidden />
          Parecer Final
        </h2>
        <button
          onClick={() => copy(opinion || '', 'final_opinion')}
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
              Copiar Parecer para o SEI
            </>
          )}
        </button>
      </div>
      <p className="whitespace-pre-wrap leading-relaxed text-content-secondary">{opinion}</p>
    </div>
  );
}
