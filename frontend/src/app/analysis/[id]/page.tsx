'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Clock, FileBarChart, Play, ChevronLeft } from 'lucide-react';
import { getDocument, startAnalysis, getDocumentAnalyses, getAnalysis, extractErrorMessage } from '@/lib/api';
import { startPolling } from '@/lib/polling';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import RevisionsTimelineModal from '@/components/RevisionsTimelineModal';
import ChatPanel from '@/components/chat/ChatPanel';
import AnalysisProgress from '@/components/analysis/AnalysisProgress';
import ItemList from '@/components/analysis/ItemList';
import ItemDetail from '@/components/analysis/ItemDetail';
import { isSeiCopyAllowed } from '@/components/analysis/CorrectionCard';
import type {
  DocumentDetailResponse,
  DocumentItemResponse,
  AnalysisDetailResponse,
  CorrectionResponse,
} from '@/types';

export default function AnalysisPage() {
  const params = useParams();
  const documentId = params.id as string;

  const [document, setDocument] = useState<DocumentDetailResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisDetailResponse | null>(null);
  const [selectedItem, setSelectedItem] = useState<DocumentItemResponse | null>(null);
  const selectedItemRef = useRef<DocumentItemResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revisionsModalOpen, setRevisionsModalOpen] = useState(false);

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
      (updated) => ['completed', 'error'].includes(updated.status),
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
      const result = await startAnalysis(documentId);

      const newAnalysis = await getAnalysis(result.analysis_id, { skipCache: true });
      setAnalysis(newAnalysis);
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao iniciar análise.'));
    } finally {
      setAnalyzing(false);
    }
  }

  function getItemCorrections(itemId: string): CorrectionResponse[] {
    if (!analysis?.corrections) return [];
    return analysis.corrections.filter((c) => c.document_item_id === itemId);
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
        <Link href="/" className="btn-primary mt-4 inline-flex">
          Voltar
        </Link>
      </div>
    );
  }

  const errorInfo = error ? getErrorMessage(error, 'analysis') : null;

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
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button variant="secondary" onClick={() => setRevisionsModalOpen(true)}>
            <Clock className="h-4 w-4" aria-hidden />
            <span className="hidden sm:inline">Histórico de Edições</span>
            <span className="sm:hidden">Histórico</span>
          </Button>

          {analysis?.status === 'completed' && (
            <Link href={`/report/${analysis.id}`}>
              <Button variant="secondary">
                <FileBarChart className="h-4 w-4" aria-hidden />
                <span className="hidden sm:inline">Ver Relatório</span>
                <span className="sm:hidden">Relatório</span>
              </Button>
            </Link>
          )}

          {(!analysis || ['completed', 'error'].includes(analysis.status)) &&
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

      {/* Erro de Requisição */}
      {errorInfo && (
        <AlertBanner variant="error" title={errorInfo.title}>
          {errorInfo.message}
        </AlertBanner>
      )}

      {/* Layout principal: itens à esquerda, detalhes à direita (empilha no mobile) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
        <ItemList
          items={document.items}
          selectedId={selectedItem?.id ?? null}
          getCorrections={getItemCorrections}
          onSelect={setSelectedItem}
        />

        {selectedItem ? (
          <ItemDetail
            item={selectedItem}
            corrections={getItemCorrections(selectedItem.id)}
            getUpdatedItemText={getUpdatedItemText}
            showCorrections={!!analysis}
          />
        ) : (
          <div className="glass-card col-span-1 p-12 text-center lg:col-span-8">
            <p className="text-content-muted">Selecione um item para ver os detalhes.</p>
          </div>
        )}
      </div>

      {/* Copiloto LicitAI */}
      <ChatPanel
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
