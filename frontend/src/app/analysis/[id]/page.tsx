'use client';

import { useState } from 'react';
import Link from 'next/link';
import { FileText } from 'lucide-react';
import { getErrorMessage } from '@/lib/errors';
import {
  countPendingPriority,
  filterItemsForPriorityMode,
} from '@/lib/priorityQueue';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import RevisionsTimelineModal from '@/components/RevisionsTimelineModal';
import ChatCopilot from '@/components/chat/ChatCopilot';
import AnalysisHeader from '@/components/analysis/AnalysisHeader';
import AnalysisBanners from '@/components/analysis/AnalysisBanners';
import Art6ChecklistPanel from '@/components/analysis/Art6ChecklistPanel';
import DiffUpdatePanel from '@/components/analysis/DiffUpdatePanel';
import GuidedReview from '@/components/analysis/GuidedReview';
import ItemList from '@/components/analysis/ItemList';
import ItemDetail from '@/components/analysis/ItemDetail';
import { isSeiCopyAllowed } from '@/components/analysis/CorrectionCard';
import { useAnalysisPage } from './useAnalysisPage';

export default function AnalysisPage() {
  const s = useAnalysisPage();
  const [guided, setGuided] = useState(false);

  if (s.loading) {
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

  if (!s.document) {
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

  const errorInfo = s.error ? getErrorMessage(s.error, 'analysis') : null;
  const document = s.document;
  const pendingPriority = s.analysis?.corrections
    ? countPendingPriority(s.analysis.corrections)
    : 0;
  const approvedCount =
    s.analysis?.corrections?.filter((c) => isSeiCopyAllowed(c.review_status)).length ?? 0;
  const analysisDone =
    s.analysis?.status === 'completed' || s.analysis?.status === 'completed_with_errors';
  const visibleItems =
    document && s.analysis
      ? filterItemsForPriorityMode(document.items, s.analysis.corrections, s.priorityMode)
      : document?.items ?? [];

  return (
    <div className="animate-fade-in space-y-6">
      <AnalysisHeader
        document={document}
        analysis={s.analysis}
        pendingPriority={pendingPriority}
        approvedCount={approvedCount}
        analysisDone={analysisDone}
        analyzing={s.analyzing}
        exporting={s.exporting}
        isCopied={s.isCopied}
        onCopySeiPack={() => void s.handleCopySeiPack()}
        onCopyCorrectedHtml={() => void s.handleCopyCorrectedHtml()}
        onDownloadDocx={() => void s.handleDownloadDocx()}
        onDownloadSeiPack={() => void s.handleDownloadSeiPack()}
        onStartAnalysis={() => void s.handleStartAnalysis()}
        onOpenRevisions={() => s.setRevisionsModalOpen(true)}
      />

      <AnalysisBanners
        analysis={s.analysis}
        analyzing={s.analyzing}
        errorTitle={errorInfo?.title ?? ''}
        errorMessage={errorInfo?.message ?? ''}
        hasError={!!errorInfo}
        onReanalyzePartial={() => void s.handleReanalyzePartial()}
        onRetry={() => void s.handleStartAnalysis()}
      />

      {analysisDone && s.analysis && (
        <Art6ChecklistPanel
          items={s.analysis.art6_checklist ?? []}
          coverage={s.analysis.art6_coverage}
          meetsTarget={s.analysis.art6_meets_target}
        />
      )}

      {s.analysis && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-content-secondary">Próximo passo:</span>
          <Button
            size="sm"
            variant={guided ? 'primary' : s.priorityMode === 'priority' ? 'primary' : 'secondary'}
            data-testid="queue-priority"
            onClick={() => {
              s.setPriorityMode('priority');
              setGuided(true);
            }}
          >
            Revisar agora
          </Button>
          <Button
            size="sm"
            variant={!guided && s.priorityMode === 'all' ? 'primary' : 'secondary'}
            data-testid="queue-all"
            onClick={() => {
              s.setPriorityMode('all');
              setGuided(false);
            }}
          >
            Ver todas
          </Button>
          {guided ? (
            <span className="text-xs text-content-muted">Modo guiado: 1 por vez, grave primeiro</span>
          ) : (
            <span className="text-xs text-content-muted">
              Comece pelas sugestões graves e partes faltantes do TR
            </span>
          )}
        </div>
      )}

      {guided && s.analysis ? (
        <GuidedReview
          analysisId={s.analysis.id}
          corrections={s.analysis.corrections}
          onReviewUpdated={s.handleReviewUpdated}
          onExit={() => setGuided(false)}
          onAfterComplete={() => {
            const el = window.document.querySelector('[data-testid="sei-pack-btn"]') as HTMLElement | null;
            el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
        {s.diffFrom && (
          <DiffUpdatePanel
            oldDocumentId={s.diffFrom}
            newDocumentId={s.documentId}
            onPickItemNumber={(itemNumber) => {
              const match = document.items.find((i) => i.item_number === itemNumber);
              if (match) s.setSelectedItem(match);
            }}
          />
        )}

        <ItemList
          items={visibleItems}
          selectedId={s.selectedItem?.id ?? null}
          getCorrections={s.getItemCorrections}
          onSelect={s.setSelectedItem}
          className={s.diffFrom ? 'lg:col-span-3' : undefined}
        />

        {s.selectedItem ? (
          <ItemDetail
            item={s.selectedItem}
            corrections={s.getItemCorrections(s.selectedItem.id)}
            getUpdatedItemText={s.getUpdatedItemText}
            showCorrections={!!s.analysis}
            onReviewUpdated={s.handleReviewUpdated}
            analyzedItemIds={s.analysis?.analyzed_item_ids}
            analysisDone={analysisDone}
            className={s.diffFrom ? 'lg:col-span-6' : undefined}
          />
        ) : (
          <div
            className={`col-span-1 rounded-lg border border-line-subtle bg-surface/30 ${s.diffFrom ? 'lg:col-span-6' : 'lg:col-span-8'}`}
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
      )}

      <ChatCopilot
        documentId={s.documentId}
        analysisId={s.analysis?.id}
        itemNumber={s.selectedItem?.item_number}
        documentLabel={document.filename_original}
        title={`Copiloto — ${document.filename_original}`}
        page="analysis"
        defaultOpen={false}
      />

      <RevisionsTimelineModal
        documentId={s.documentId}
        isOpen={s.revisionsModalOpen}
        onClose={() => s.setRevisionsModalOpen(false)}
        onRestored={() => s.loadData(true)}
      />
    </div>
  );
}
