'use client';

import {
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
import { copy } from '@/lib/copy';

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
        <h1 className="max-w-xl truncate text-xl font-semibold tracking-tight text-content-primary sm:text-2xl">
          {document.filename_original}
        </h1>
        <p className="tnum mt-1 text-sm text-content-muted">
          {analysis ? (
            <>
              {pendingPriority > 0
                ? `${pendingPriority} para revisar agora`
                : 'Nada urgente para revisar'}
              {approvedCount > 0 ? ` · ${approvedCount} prontas para o SEI` : ''}
            </>
          ) : (
            'Ainda sem análise'
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
              title={approvedCount === 0 ? copy.cta.copySeiDisabled : copy.cta.copySeiOk}
              onClick={onCopySeiPack}
            >
              <ClipboardCopy className="h-4 w-4" aria-hidden />
              {isCopied('sei_pack') ? copy.cta.copySeiDone : copy.cta.copySei}
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
