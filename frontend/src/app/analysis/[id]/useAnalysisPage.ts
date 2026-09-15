'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { toast } from 'sonner';
import {
  downloadCorrectedDocx,
  extractErrorMessage,
  getAnalysis,
  getCorrectedHtml,
  getDocument,
  getDocumentAnalyses,
  getSeiPack,
  reanalyzePartial,
  startAnalysis,
} from '@/lib/api';
import { startPolling } from '@/lib/polling';
import { useCopy } from '@/lib/useCopy';
import {
  filterPriorityCorrections,
  type PriorityMode,
} from '@/lib/priorityQueue';
import { isSeiCopyAllowed } from '@/components/analysis/CorrectionCard';
import type {
  AnalysisDetailResponse,
  CorrectionResponse,
  DocumentDetailResponse,
  DocumentItemResponse,
} from '@/types';

/** Estado + ações da página de análise — extraído de `app/analysis/[id]/page.tsx`. */
export function useAnalysisPage() {
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

  return {
    documentId,
    diffFrom,
    document,
    analysis,
    selectedItem,
    setSelectedItem,
    loading,
    analyzing,
    error,
    revisionsModalOpen,
    setRevisionsModalOpen,
    priorityMode,
    setPriorityMode,
    exporting,
    copy,
    isCopied,
    loadData,
    handleStartAnalysis,
    handleReanalyzePartial,
    handleCopySeiPack,
    handleDownloadSeiPack,
    handleCopyCorrectedHtml,
    handleDownloadDocx,
    getItemCorrections,
    getUpdatedItemText,
    handleReviewUpdated,
  };
}

export type AnalysisPageState = ReturnType<typeof useAnalysisPage>;
