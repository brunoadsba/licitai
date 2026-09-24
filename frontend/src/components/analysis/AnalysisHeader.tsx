'use client';

import Link from 'next/link';
import {
  ChevronLeft,
  ClipboardCopy,
  Clock,
  FileBarChart,
  FileCode2,
  FileDown,
  FileType,
  MoreHorizontal,
  Play,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/DropdownMenu';
import type {
  AnalysisDetailResponse,
  DocumentDetailResponse,
} from '@/types';

interface AnalysisHeaderProps {
  document: DocumentDetailResponse;
  analysis: AnalysisDetailResponse | null;
  pendingPriority: number;
  approvedCount: number;
  analysisDone: boolean;
  analyzing: boolean;
  exporting: 'pack' | 'html' | 'docx' | 'audit' | null;
  isCopied: (key: string) => boolean;
  onCopySeiPack: () => void;
  onCopyCorrectedHtml: () => void;
  onDownloadDocx: () => void;
  onDownloadSeiPack: () => void;
  onDownloadAuditPack: () => void;
  onStartAnalysis: () => void;
  onOpenRevisions: () => void;
}

/** Cabeçalho da página de análise — extraído de `app/analysis/[id]/page.tsx`. */
export default function AnalysisHeader({
  document,
  analysis,
  pendingPriority,
  approvedCount,
  analysisDone,
  analyzing,
  exporting,
  isCopied,
  onCopySeiPack,
  onCopyCorrectedHtml,
  onDownloadDocx,
  onDownloadSeiPack,
  onDownloadAuditPack,
  onStartAnalysis,
  onOpenRevisions,
}: AnalysisHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="mb-1 flex items-center gap-1.5 text-xs text-content-subtle">
          <Link
            href="/"
            className="inline-flex items-center gap-0.5 outline-none transition-colors hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
          >
            <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
            Painel
          </Link>
          <span aria-hidden>/</span>
          <span className="text-content-muted">Análise</span>
        </div>
        <h1 className="max-w-xl truncate text-xl font-semibold tracking-tight text-content-primary sm:text-2xl">
          {document.filename_original}
        </h1>
        <p className="tnum mt-1 text-sm text-content-muted">
          {document.total_items} itens · {document.file_type.toUpperCase()}
          {analysis && (
            <>
              {' '}
              · {pendingPriority} para revisar agora
              {approvedCount > 0 ? ` · ${approvedCount} prontas para o SEI` : ''}
            </>
          )}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {analysisDone && (
          <>
            <Button
              variant="primary"
              loading={exporting === 'pack'}
              disabled={approvedCount === 0}
              data-testid="sei-pack-btn"
              title={
                approvedCount === 0
                  ? 'Aprove ou ajuste ao menos uma correção'
                  : 'Copiar pacote com correções aprovadas/ajustadas'
              }
              onClick={onCopySeiPack}
            >
              <ClipboardCopy className="h-4 w-4" aria-hidden />
              {isCopied('sei_pack') ? 'Pacote copiado' : 'Copiar pacote SEI'}
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger
                className="inline-flex h-10 select-none items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-line-strong bg-white/[0.03] px-4 text-sm font-medium text-content-secondary outline-none transition-all hover:bg-white/[0.07] hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
                aria-label="Exportar"
              >
                Exportar
                <FileDown className="h-4 w-4" aria-hidden />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Formatos</DropdownMenuLabel>
                <DropdownMenuItem
                  disabled={exporting !== null || approvedCount === 0}
                  onSelect={onCopyCorrectedHtml}
                >
                  <FileCode2 className="h-4 w-4" aria-hidden />
                  {isCopied('corrected_html') ? 'HTML copiado' : 'Copiar TR corrigido (HTML)'}
                </DropdownMenuItem>
                <DropdownMenuItem
                  disabled={exporting !== null || approvedCount === 0}
                  onSelect={onDownloadDocx}
                >
                  <FileType className="h-4 w-4" aria-hidden />
                  Baixar DOCX
                </DropdownMenuItem>
                <DropdownMenuItem
                  disabled={exporting !== null || approvedCount === 0}
                  onSelect={onDownloadSeiPack}
                >
                  <FileDown className="h-4 w-4" aria-hidden />
                  Baixar pacote (.md)
                </DropdownMenuItem>
                <DropdownMenuItem
                  disabled={exporting !== null}
                  onSelect={onDownloadAuditPack}
                >
                  <FileBarChart className="h-4 w-4" aria-hidden />
                  Pacote de auditoria (.json)
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        )}

        <DropdownMenu>
          <DropdownMenuTrigger
            className="inline-flex h-10 select-none items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-line-strong bg-white/[0.03] px-4 text-sm font-medium text-content-secondary outline-none transition-all hover:bg-white/[0.07] hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
            aria-label="Mais ações"
          >
            <MoreHorizontal className="h-4 w-4" aria-hidden />
            <span className="hidden sm:inline">Mais</span>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={onOpenRevisions}>
              <Clock className="h-4 w-4" aria-hidden />
              Histórico de edições
            </DropdownMenuItem>
            {analysisDone && analysis && (
              <DropdownMenuItem
                onSelect={() => {
                  window.location.href = `/report/${analysis.id}`;
                }}
              >
                <FileBarChart className="h-4 w-4" aria-hidden />
                Ver relatório
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            {(!analysis ||
              ['completed', 'completed_with_errors', 'error'].includes(analysis.status)) &&
              document.status !== 'error' && (
                <DropdownMenuItem
                  disabled={analyzing}
                  onSelect={onStartAnalysis}
                >
                  <Play className="h-4 w-4" aria-hidden />
                  {analysis?.status === 'error'
                    ? 'Tentar novamente'
                    : analysis
                      ? 'Reanalisar'
                      : 'Iniciar análise'}
                </DropdownMenuItem>
              )}
          </DropdownMenuContent>
        </DropdownMenu>

        {!analysis && document.status !== 'error' && (
          <Button onClick={onStartAnalysis} loading={analyzing}>
            {!analyzing && <Play className="h-4 w-4" aria-hidden />}
            Iniciar análise
          </Button>
        )}
      </div>
    </div>
  );
}
