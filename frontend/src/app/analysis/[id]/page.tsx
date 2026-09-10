'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Clock, FileBarChart, Play, ChevronLeft, ClipboardCopy, FileCode2, FileDown, FileType } from 'lucide-react';
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
import { Skeleton } from '@/components/ui/Skeleton';
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
      <div className="glass-card p-12 text-center">
        <p className="text-content-muted">Documento não encontrado.</p>
        <Link href="/" className="mt-4 inline-flex">
          <Button>Voltar</Button>
        </Link>
      </div>
    );
  }

  const errorInfo = error ? getErrorMessage(error, 'analysis') : null;
  const pendingPriority = analysis?.corrections
    ? countPendingPriority(analysis.corrections)
    : 0;
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
                · {pendingPriority} aguardando revisão prioritária
              </>
            )}
          </p>
          <p className="mt-1 text-xs text-content-subtle">
            IA sugere; você decide. Só o aprovado vai ao SEI.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {(analysis?.status === 'completed' || analysis?.status === 'completed_with_errors') && (
            <>
              <Button
                variant="secondary"
                loading={exporting === 'pack'}
                onClick={() => void handleCopySeiPack()}
              >
                <ClipboardCopy className="h-4 w-4" aria-hidden />
                {isCopied('sei_pack') ? 'Pacote copiado' : 'Copiar pacote SEI'}
              </Button>
              <Button
                variant="secondary"
                loading={exporting === 'pack'}
                onClick={() => void handleDownloadSeiPack()}
              >
                <FileDown className="h-4 w-4" aria-hidden />
                Baixar .md
              </Button>
              <Button
                variant="secondary"
                loading={exporting === 'html'}
                onClick={() => void handleCopyCorrectedHtml()}
              >
                <FileCode2 className="h-4 w-4" aria-hidden />
                {isCopied('corrected_html') ? 'HTML copiado' : 'Copiar TR corrigido'}
              </Button>
              <Button
                variant="secondary"
                loading={exporting === 'docx'}
                onClick={() => void handleDownloadDocx()}
              >
                <FileType className="h-4 w-4" aria-hidden />
                Baixar DOCX
              </Button>
            </>
          )}
          <Button variant="secondary" onClick={() => setRevisionsModalOpen(true)}>
            <Clock className="h-4 w-4" aria-hidden />
            <span className="hidden sm:inline">Histórico de Edições</span>
            <span className="sm:hidden">Histórico</span>
          </Button>

          {(analysis?.status === 'completed' || analysis?.status === 'completed_with_errors') && (
            <Link href={`/report/${analysis.id}`}>
              <Button variant="secondary">
                <FileBarChart className="h-4 w-4" aria-hidden />
                <span className="hidden sm:inline">Ver Relatório</span>
                <span className="sm:hidden">Relatório</span>
              </Button>
            </Link>
          )}

          {(!analysis || ['completed', 'completed_with_errors', 'error'].includes(analysis.status)) &&
            document.status !== 'error' && (
              <Button onClick={handleStartAnalysis} loading={analyzing}>
                {!analyzing && <Play className="h-4 w-4" aria-hidden />}
                {analysis?.status === 'error'
                  ? 'Tentar Novamente'
                  : analysis
                    ? 'Reanalisar'
                    : 'Iniciar Análise'}
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
              Tentar Novamente
            </Button>
          }
        >
          {analysis.error_message || 'Erro interno ou reinicialização do servidor.'}
        </AlertBanner>
      )}

      {analysis?.status === 'completed_with_errors' && (
        <AlertBanner
          variant="warning"
          title="Análise concluída com cobertura incompleta"
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
            'Um ou mais agentes/itens falharam. Não trate todos os itens como adequados.'}
        </AlertBanner>
      )}
      {/* Erro de Requisição */}
      {errorInfo && (
        <AlertBanner variant="error" title={errorInfo.title}>
          {errorInfo.message}
        </AlertBanner>
      )}

      {analysis && (analysis.status === 'completed' || analysis.status === 'completed_with_errors') && (
        <Art6ChecklistPanel items={analysis.art6_checklist ?? []} />
      )}

      {/* Layout principal: itens à esquerda, detalhes à direita (empilha no mobile) */}
      {analysis && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-content-muted">Fila:</span>
          <Button
            size="sm"
            variant={priorityMode === 'priority' ? 'primary' : 'secondary'}
            onClick={() => setPriorityMode('priority')}
          >
            Prioridade
          </Button>
          <Button
            size="sm"
            variant={priorityMode === 'all' ? 'primary' : 'secondary'}
            onClick={() => setPriorityMode('all')}
          >
            Ver todas
          </Button>
          <span className="text-xs text-content-subtle">
            Prioridade = alto/crítico + estrutural (Art. 6º)
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
            className={`glass-card col-span-1 p-12 text-center ${diffFrom ? 'lg:col-span-6' : 'lg:col-span-8'}`}
          >
            <p className="text-content-muted">Selecione um item para ver os detalhes.</p>
          </div>
        )}
      </div>

      {/* Copiloto LicitAI */}
      <ChatCopilot
        documentId={documentId}
        analysisId={analysis?.id}
        itemNumber={selectedItem?.item_number}
        title={`Copiloto — ${document.filename_original}`}
        page="analysis"
      />

      {/* Modal de Histórico e Versionamento de Edições (Single-User) */}
      <RevisionsTimelineModal
        documentId={documentId}
        isOpen={revisionsModalOpen}
        onClose={() => setRevisionsModalOpen(false)}
        onRestored={() => loadData(true)}
      />
    </div>
  );
}
