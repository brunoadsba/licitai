'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getDocument, startAnalysis, getDocumentAnalyses, getAnalysis } from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import RevisionsTimelineModal from '@/components/RevisionsTimelineModal';
import ChatPanel from '@/components/chat/ChatPanel';
import AnalysisProgress from '@/components/analysis/AnalysisProgress';
import ItemList from '@/components/analysis/ItemList';
import ItemDetail from '@/components/analysis/ItemDetail';
import type {
  DocumentDetailResponse,
  DocumentItemResponse,
  AnalysisDetailResponse,
  CorrectionResponse,
} from '@/types';

export default function AnalysisPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.id as string;

  const [document, setDocument] = useState<DocumentDetailResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisDetailResponse | null>(null);
  const [selectedItem, setSelectedItem] = useState<DocumentItemResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revisionsModalOpen, setRevisionsModalOpen] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const doc = await getDocument(documentId);
      setDocument(doc);

      if (doc.items.length > 0 && !selectedItem) {
        setSelectedItem(doc.items[0]);
      }

      // Carregar análise mais recente
      const analyses = await getDocumentAnalyses(documentId);
      if (analyses.length > 0) {
        setAnalysis(analyses[0]);
      }
    } catch {
      setError('Erro ao carregar documento.');
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Polling em tempo real durante a análise (1 segundo)
  useEffect(() => {
    if (!analysis || !['pending', 'running'].includes(analysis.status)) return;

    const interval = setInterval(async () => {
      try {
        const updated = await getAnalysis(analysis.id);
        setAnalysis(updated);

        if (['completed', 'error'].includes(updated.status)) {
          clearInterval(interval);
        }
      } catch {
        // silenciar erros de polling
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [analysis?.id, analysis?.status]);

  async function handleStartAnalysis() {
    try {
      setAnalyzing(true);
      setError(null);
      const result = await startAnalysis(documentId);

      // Carregar a análise criada
      const newAnalysis = await getAnalysis(result.analysis_id);
      setAnalysis(newAnalysis);
    } catch (err: any) {
      setError(err.message || 'Erro ao iniciar análise.');
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
      if (c.original_text && c.suggested_text && text.includes(c.original_text)) {
        text = text.replace(c.original_text, c.suggested_text);
      }
    }
    return text;
  }

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="skeleton h-12 w-64" />
        <div className="grid grid-cols-4 gap-4">
          <div className="skeleton h-[600px]" />
          <div className="col-span-3 skeleton h-[600px]" />
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="glass-card p-12 text-center">
        <p className="text-gray-400">Documento não encontrado.</p>
        <Link href="/" className="btn-primary mt-4 inline-flex">Voltar</Link>
      </div>
    );
  }

  const errorInfo = error ? getErrorMessage(error, 'analysis') : null;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
            <Link href="/" className="hover:text-gray-300 transition-colors">Painel</Link>
            <span>›</span>
            <span className="text-gray-400">Análise</span>
          </div>
          <h1 className="text-xl font-bold text-white truncate max-w-xl">
            {document.filename_original}
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            {document.total_items} itens • {document.file_type.toUpperCase()}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setRevisionsModalOpen(true)}
            className="btn-secondary"
            title="Ver e salvar histórico de edições/snapshots"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Histórico de Edições
          </button>

          {analysis?.status === 'completed' && (
            <Link
              href={`/report/${analysis.id}`}
              className="btn-secondary"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
              </svg>
              Ver Relatório
            </Link>
          )}

          {(!analysis || ['completed', 'error'].includes(analysis.status)) && document.status !== 'error' && (
            <button
              onClick={handleStartAnalysis}
              disabled={analyzing}
              className="btn-primary"
            >
              {analyzing ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Iniciando...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
                  </svg>
                  {analysis?.status === 'error' ? 'Tentar Novamente' : (analysis ? 'Reanalisar' : 'Iniciar Análise')}
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Barra de progresso da análise com estilo premium */}
      {analysis && ['pending', 'running'].includes(analysis.status) && (
        <AnalysisProgress analysis={analysis} />
      )}

      {/* Banner de erro da análise */}
      {analysis?.status === 'error' && (
        <AlertBanner
          variant="error"
          title="A análise anterior foi interrompida"
          action={
            <button
              onClick={handleStartAnalysis}
              disabled={analyzing}
              className="btn-primary text-xs"
            >
              Tentar Novamente com IA
            </button>
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

      {/* Layout principal: itens à esquerda, detalhes à direita */}
      <div className="grid grid-cols-12 gap-6">
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
          <div className="glass-card p-12 text-center col-span-8">
            <p className="text-gray-500">Selecione um item para ver os detalhes.</p>
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
        onRestored={() => loadData()}
      />
    </div>
  );
}
