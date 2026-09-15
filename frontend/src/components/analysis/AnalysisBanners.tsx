'use client';

import AlertBanner from '@/components/ui/AlertBanner';
import { Button } from '@/components/ui/Button';
import AnalysisProgress from '@/components/analysis/AnalysisProgress';
import type { AnalysisDetailResponse } from '@/types';

interface AnalysisBannersProps {
  analysis: AnalysisDetailResponse | null;
  analyzing: boolean;
  errorTitle: string;
  errorMessage: string;
  hasError: boolean;
  onReanalyzePartial: () => void;
  onRetry: () => void;
}

/** Banners de progresso/erro da análise — extraído de `app/analysis/[id]/page.tsx`. */
export default function AnalysisBanners({
  analysis,
  analyzing,
  errorTitle,
  errorMessage,
  hasError,
  onReanalyzePartial,
  onRetry,
}: AnalysisBannersProps) {
  return (
    <>
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
            <Button size="sm" onClick={onRetry} loading={analyzing}>
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
          title={
            analysis.budget_truncated ||
            (analysis.error_message?.includes('itens prioritários') ?? false) ||
            (analysis.error_message?.includes('ANALYSIS_MAX_LLM_CALLS') ?? false)
              ? 'Análise preliminar concluída'
              : 'Análise concluída, mas alguns trechos falharam'
          }
          action={
            <Button size="sm" onClick={() => void onReanalyzePartial()} loading={analyzing}>
              Reanalisar faltantes
            </Button>
          }
        >
          {analysis.budget_truncated ||
          analysis.error_message?.includes('itens prioritários') ||
          analysis.error_message?.includes('ANALYSIS_MAX_LLM_CALLS')
            ? 'Análise preliminar de itens prioritários concluída. Para auditar os demais trechos substantivos, utilize "Reanalisar faltantes".'
            : analysis.error_message ||
              'Parte da análise falhou. Não trate todos os itens como adequados.'}
        </AlertBanner>
      )}
      {hasError && (
        <AlertBanner variant="error" title={errorTitle}>
          {errorMessage}
        </AlertBanner>
      )}
    </>
  );
}
