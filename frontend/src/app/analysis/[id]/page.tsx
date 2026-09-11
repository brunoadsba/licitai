'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  Clock,
  FileBarChart,
  FileText,
  Play,
  ChevronLeft,
  ClipboardCopy,
  FileCode2,
  FileDown,
  FileType,
  MoreHorizontal,
} from 'lucide-react';
import {
  getDocument,
  startAnalysis,
  getDocumentAnalyses,
  getAnalysis,
  getSeiPack,
  getCorrectedHtml,
  downloadCorrectedDocx,
  reanalyzePartial,
  extractErrorMessage,
} from '@/lib/api';
import { startPolling } from '@/lib/polling';
import { getErrorMessage } from '@/lib/errors';
import { useCopy } from '@/lib/useCopy';
import {
  countPendingPriority,
  filterItemsForPriorityMode,
  filterPriorityCorrections,
  type PriorityMode,
} from '@/lib/priorityQueue';
import AlertBanner from '@/components/ui/AlertBanner';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/DropdownMenu';
import RevisionsTimelineModal from '@/components/RevisionsTimelineModal';
import ChatCopilot from '@/components/chat/ChatCopilot';
import AnalysisProgress from '@/components/analysis/AnalysisProgress';
import Art6ChecklistPanel from '@/components/analysis/Art6ChecklistPanel';
import DiffUpdatePanel from '@/components/analysis/DiffUpdatePanel';
import ItemList from '@/components/analysis/ItemList';
import ItemDetail from '@/components/analysis/ItemDetail';
import { isSeiCopyAllowed } from '@/components/analysis/CorrectionCard';
import type {
  DocumentDetailResponse,
  DocumentItemResponse,
  AnalysisDetailResponse,
  CorrectionResponse,
} from '@/types';
import { toast } from 'sonner';

export default function AnalysisPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const documentId = params.id as string;
  const diffFrom = searchParams.get('diffFrom');

  const [document, setDocument] = useState<DocumentDetailResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisDetailResponse | null>(null);
  const [selectedItem, setSelectedItem] = useState<DocumentItemResponse | null>(null);
  const selectedItemRef = useRef<DocumentItemResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revisionsModalOpen, setRevisionsModalOpen] = useState(false);
  const [priorityMode, setPriorityMode] = useState<PriorityMode>('priority');
  const [exporting, setExporting] = useState<'pack' | 'html' | 'docx' | null>(null);
  const { copy, isCopied } = useCopy();

  useEffect(() => {
    selectedItemRef.current = selectedItem;
  }, [selectedItem]);

  const loadData = useCallback(
    async (keepSelectedItem = false) => {
      try {
        setLoading(true);
        const doc = await getDocument(documentId);
        setDocument(doc);

        if (keepSelectedItem) {
          const current = selectedItemRef.current;
          if (current) {
            const stillExists = doc.items.find((i) => i.id === current.id) ?? null;
            setSelectedItem(stillExists);
          }
        } else if (doc.items.length > 0) {
          setSelectedItem(doc.items[0]);
        } else {
          setSelectedItem(null);
        }

        const analyses = await getDocumentAnalyses(documentId);
        if (analyses.length > 0) {
          setAnalysis(analyses[0]);
        }
      } catch {
        setError('Erro ao carregar documento.');
      } finally {
        setLoading(false);
      }
    },
    [documentId],
  );

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  // Polling em tempo real durante a análise
  useEffect(() => {
    if (!analysis || !['pending', 'running'].includes(analysis.status)) return;

    const analysisId = analysis.id;
    const { cancel } = startPolling(
      () => getAnalysis(analysisId, { skipCache: true }),
      (updated) => ['completed', 'completed_with_errors', 'error'].includes(updated.status),
      {
        initialIntervalMs: 1000,
        maxIntervalMs: 8000,
        deadlineMs: 30 * 60 * 1000,
        maxFailures: 8,
        onResult: (updated) => {
          setAnalysis(updated);
        },
      }
    );

    return () => cancel();
    // Intencional: reagir só a id/status, não a cada tick de progresso
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis?.id, analysis?.status]);

  async function handleStartAnalysis() {
    try {
      setAnalyzing(true);
      setError(null);
      const result = await startAnalysis(documentId, 'economic');

      const newAnalysis = await getAnalysis(result.analysis_id, { skipCache: true });
      setAnalysis(newAnalysis);
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao iniciar análise.'));
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleReanalyzePartial() {
    if (!analysis) return;
    try {
      setAnalyzing(true);
      setError(null);
      const result = await reanalyzePartial(analysis.id);
      const newAnalysis = await getAnalysis(result.analysis_id, { skipCache: true });
      setAnalysis(newAnalysis);
      toast.success('Reanálise parcial enfileirada');
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Não foi possível reanalisar parcialmente.'));
    } finally {
      setAnalyzing(false);
    }
  }

  function downloadText(filename: string, text: string) {
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = window.document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleCopySeiPack() {
    if (!analysis) return;
    try {
      setExporting('pack');
      const pack = await getSeiPack(analysis.id);
      if (pack.total === 0) {
        toast.message('Nenhuma correção aprovada/ajustada ainda.');
        return;
      }
      await navigator.clipboard.writeText(pack.text);
      copy(pack.text, 'sei_pack');
      toast.success(`Pacote SEI copiado (${pack.total} correções)`);
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Não foi possível montar o pacote SEI.'));
    } finally {
      setExporting(null);
    }
  }

  async function handleDownloadSeiPack() {
    if (!analysis) return;
    try {
      setExporting('pack');
      const pack = await getSeiPack(analysis.id);
      if (pack.total === 0) {
        toast.message('Nenhuma correção aprovada/ajustada ainda.');
        return;
      }
      downloadText(`pacote-sei-${analysis.id.slice(0, 8)}.md`, pack.text);
      toast.success('Pacote SEI baixado');
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Não foi possível baixar o pacote SEI.'));
    } finally {
      setExporting(null);
    }
  }

  async function handleCopyCorrectedHtml() {
    if (!analysis) return;
    try {
      setExporting('html');
      const data = await getCorrectedHtml(analysis.id);
      await navigator.clipboard.writeText(data.html);
      copy(data.html, 'corrected_html');
      const skipped = data.skipped_corrections?.length ?? 0;
      if (skipped > 0) {
        toast.message(
          `TR copiado com ${data.applied_corrections} aplicadas; ${skipped} não encontradas no texto.`,
        );
      } else {
        toast.success(`TR corrigido copiado (${data.applied_corrections} correções)`);
      }
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Não foi possível montar o TR corrigido.'));
    } finally {
      setExporting(null);
    }
  }

  async function handleDownloadDocx() {
    if (!analysis) return;
    try {
      setExporting('docx');
      const result = await downloadCorrectedDocx(analysis.id);
      if (result.skipped > 0) {
        toast.message(
          `DOCX baixado (${result.applied} aplicadas; ${result.skipped} skips).`,
        );
      } else {
        toast.success(`DOCX baixado (${result.applied} correções)`);
      }
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Não foi possível gerar o DOCX.'));
    } finally {
      setExporting(null);
    }
  }

  function getItemCorrections(itemId: string): CorrectionResponse[] {
    if (!analysis?.corrections) return [];
    return filterPriorityCorrections(
      analysis.corrections.filter((c) => c.document_item_id === itemId),
      priorityMode,
    );
  }

  function getUpdatedItemText(item: DocumentItemResponse, corrections: CorrectionResponse[]): string {
    let text = item.content;
    for (const c of corrections) {
      if (!isSeiCopyAllowed(c.review_status)) continue;
      if (c.original_text && c.suggested_text && text.includes(c.original_text)) {
        text = text.replace(c.original_text, c.suggested_text);
      }
    }
    return text;
  }

  function handleReviewUpdated(updated: CorrectionResponse) {
    setAnalysis((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        corrections: prev.corrections.map((c) => (c.id === updated.id ? updated : c)),
      };
    });
  }

  if (loading) {
    return (
      <div className="animate-fade-in space-y-4">
        <Skeleton className="h-12 w-64" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <Skeleton className="h-[480px] lg:col-span-4" />
          <Skeleton className="h-[480px] lg:col-span-8" />
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <EmptyState
        icon={FileText}
        title="Documento não encontrado"
        description="O TR pode ter sido removido ou o link está incorreto."
        action={
          <Link href="/">
            <Button>Voltar ao Painel</Button>
          </Link>
        }
      />
    );
  }

  const errorInfo = error ? getErrorMessage(error, 'analysis') : null;
  const pendingPriority = analysis?.corrections
    ? countPendingPriority(analysis.corrections)
    : 0;
  const approvedCount =
    analysis?.corrections?.filter((c) => isSeiCopyAllowed(c.review_status)).length ?? 0;
  const analysisDone =
    analysis?.status === 'completed' || analysis?.status === 'completed_with_errors';
  const visibleItems =
    document && analysis
      ? filterItemsForPriorityMode(document.items, analysis.corrections, priorityMode)
      : document?.items ?? [];

  return (
    <div className="animate-fade-in space-y-6">
      {/* Cabeçalho */}
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
                onClick={() => void handleCopySeiPack()}
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
                    onSelect={() => void handleCopyCorrectedHtml()}
                  >
                    <FileCode2 className="h-4 w-4" aria-hidden />
                    {isCopied('corrected_html') ? 'HTML copiado' : 'Copiar TR corrigido (HTML)'}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={exporting !== null || approvedCount === 0}
                    onSelect={() => void handleDownloadDocx()}
                  >
                    <FileType className="h-4 w-4" aria-hidden />
                    Baixar DOCX
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={exporting !== null || approvedCount === 0}
                    onSelect={() => void handleDownloadSeiPack()}
                  >
                    <FileDown className="h-4 w-4" aria-hidden />
                    Baixar pacote (.md)
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
              <DropdownMenuItem onSelect={() => setRevisionsModalOpen(true)}>
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
                    onSelect={() => void handleStartAnalysis()}
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
            <Button onClick={handleStartAnalysis} loading={analyzing}>
              {!analyzing && <Play className="h-4 w-4" aria-hidden />}
              Iniciar análise
            </Button>
          )}
        </div>
      </div>

      {/* Barra de progresso da análise */}
      {analysis && ['pending', 'running'].includes(analysis.status) && (
        <AnalysisProgress analysis={analysis} />
      )}

      {/* Banner de erro da análise */}
      {analysis?.status === 'error' && (
        <AlertBanner
          variant="error"
          title="A análise anterior foi interrompida"
          action={
            <Button size="sm" onClick={handleStartAnalysis} loading={analyzing}>
              Tentar novamente
            </Button>
          }
        >
          {analysis.error_message || 'Erro interno ou reinicialização do servidor.'}
        </AlertBanner>
      )}

      {analysis?.status === 'completed_with_errors' && (
        <AlertBanner
          variant="warning"
          title="Análise concluída, mas alguns trechos falharam"
          action={
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="secondary" onClick={() => void handleReanalyzePartial()} loading={analyzing}>
                Reanalisar faltantes
              </Button>
              <Button size="sm" onClick={handleStartAnalysis} loading={analyzing}>
                Reanalisar
              </Button>
            </div>
          }
        >
          {analysis.error_message ||
            'Parte da análise falhou. Não trate todos os itens como adequados.'}
        </AlertBanner>
      )}
      {errorInfo && (
        <AlertBanner variant="error" title={errorInfo.title}>
          {errorInfo.message}
        </AlertBanner>
      )}

      {analysisDone && analysis && (
        <Art6ChecklistPanel
          items={analysis.art6_checklist ?? []}
          coverage={analysis.art6_coverage}
          meetsTarget={analysis.art6_meets_target}
        />
      )}

      {analysis && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-content-muted">Fila:</span>
          <Button
            size="sm"
            variant={priorityMode === 'priority' ? 'primary' : 'secondary'}
            data-testid="queue-priority"
            onClick={() => setPriorityMode('priority')}
          >
            Revisar agora
          </Button>
          <Button
            size="sm"
            variant={priorityMode === 'all' ? 'primary' : 'secondary'}
            data-testid="queue-all"
            onClick={() => setPriorityMode('all')}
          >
            Ver todas
          </Button>
          <span className="text-xs text-content-subtle">
            Sugestões graves e partes faltantes do TR
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
        {diffFrom && (
          <DiffUpdatePanel
            oldDocumentId={diffFrom}
            newDocumentId={documentId}
            onPickItemNumber={(itemNumber) => {
              const match = document.items.find((i) => i.item_number === itemNumber);
              if (match) setSelectedItem(match);
            }}
          />
        )}

        <ItemList
          items={visibleItems}
          selectedId={selectedItem?.id ?? null}
          getCorrections={getItemCorrections}
          onSelect={setSelectedItem}
          className={diffFrom ? 'lg:col-span-3' : undefined}
        />

        {selectedItem ? (
          <ItemDetail
            item={selectedItem}
            corrections={getItemCorrections(selectedItem.id)}
            getUpdatedItemText={getUpdatedItemText}
            showCorrections={!!analysis}
            onReviewUpdated={handleReviewUpdated}
            className={diffFrom ? 'lg:col-span-6' : undefined}
          />
        ) : (
          <div
            className={`col-span-1 rounded-lg border border-line-subtle bg-surface/30 ${diffFrom ? 'lg:col-span-6' : 'lg:col-span-8'}`}
          >
            <EmptyState
              icon={FileText}
              title="Selecione um item"
              description="Escolha um item à esquerda para ver o texto e as correções sugeridas."
              className="py-12"
            />
          </div>
        )}
      </div>

      <ChatCopilot
        documentId={documentId}
        analysisId={analysis?.id}
        itemNumber={selectedItem?.item_number}
        title={`Copiloto — ${document.filename_original}`}
        page="analysis"
        defaultOpen={false}
      />

      <RevisionsTimelineModal
        documentId={documentId}
        isOpen={revisionsModalOpen}
        onClose={() => setRevisionsModalOpen(false)}
        onRestored={() => loadData(true)}
      />
    </div>
  );
}
