'use client';

import Link from 'next/link';
import { ArrowLeft, ClipboardCopy, FileDown } from 'lucide-react';
import { Button } from '@/components/ui/Button';

/** Cabeçalho do relatório — extraído de `app/report/[id]/page.tsx`. */
export default function ReportHeader({ documentId, documentName }: { documentId: string; documentName: string }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div>
        <div className="mb-1 flex items-center gap-1.5 text-xs text-content-subtle no-print">
          <Link href="/" className="outline-none transition-colors hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60">
            Painel
          </Link>
          <span aria-hidden>/</span>
          <Link
            href={`/analysis/${documentId}`}
            className="outline-none transition-colors hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
          >
            Análise
          </Link>
          <span aria-hidden>/</span>
          <span className="text-content-muted">Relatório</span>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-content-primary">Relatório de Análise</h1>
        <p className="mt-1 text-sm text-content-muted">{documentName}</p>
        <p className="mt-1 text-xs text-content-subtle no-print">
          Resumo para leitura e impressão. Para copiar o pacote SEI, use a tela de análise.
        </p>
      </div>

      <div className="no-print flex flex-wrap items-center gap-2">
        <Link href={`/analysis/${documentId}`}>
          <Button>
            <ClipboardCopy className="h-4 w-4" aria-hidden />
            Ir à análise (exportar SEI)
          </Button>
        </Link>
        <Button
          type="button"
          variant="secondary"
          onClick={() => window.print()}
          title="Abre o diálogo de impressão do navegador (Salvar como PDF)"
        >
          <FileDown className="h-4 w-4" aria-hidden />
          Exportar PDF
        </Button>
        <Link href={`/analysis/${documentId}`}>
          <Button variant="secondary">
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Voltar
          </Button>
        </Link>
      </div>
    </div>
  );
}
