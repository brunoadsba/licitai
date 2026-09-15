'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { FileText } from 'lucide-react';
import { getReport } from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import CorrectionAccordion from '@/components/report/CorrectionAccordion';
import ReportHeader from '@/components/report/ReportHeader';
import ReportScores from '@/components/report/ReportScores';
import ReportSummaryCards from '@/components/report/ReportSummaryCards';
import ReportDistributions from '@/components/report/ReportDistributions';
import ReportOpinion from '@/components/report/ReportOpinion';
import ReportArt6 from '@/components/report/ReportArt6';
import type { ReportResponse } from '@/types';
import { filterPriorityCorrections } from '@/lib/priorityQueue';
import { PRIORITY_SECTION_TITLE } from '@/lib/copy/elaborador';

export default function ReportPage() {
  const params = useParams();
  const analysisId = params.id as string;

  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getReport(analysisId);
        setReport(data);
      } catch {
        setError('Erro ao carregar relatório.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [analysisId]);

  if (loading) {
    return (
      <div className="animate-fade-in space-y-6">
        <Skeleton className="h-12 w-64" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (error) {
    const errInfo = getErrorMessage(error, 'analysis');
    return (
      <div className="animate-fade-in space-y-4">
        <AlertBanner variant="error" title={errInfo.title}>
          {errInfo.message}
        </AlertBanner>
        <Link href="/">
          <Button>Voltar ao Painel</Button>
        </Link>
      </div>
    );
  }

  if (!report) {
    return (
      <EmptyState
        icon={FileText}
        title="Relatório não encontrado"
        description="Volte à análise ou ao painel e tente novamente."
        action={
          <Link href="/">
            <Button>Voltar ao Painel</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="print-root animate-fade-in space-y-8">
      <ReportHeader documentId={report.document_id} documentName={report.document_name} />
      <ReportScores report={report} />
      <ReportSummaryCards report={report} />
      <ReportDistributions report={report} />

      {report.final_opinion && <ReportOpinion opinion={report.final_opinion} />}

      <ReportArt6 report={report} />

      {filterPriorityCorrections(report.corrections, 'priority').length > 0 && (
        <div className="space-y-2">
          <h2 className="text-lg font-semibold tracking-tight text-content-primary">
            {PRIORITY_SECTION_TITLE}
          </h2>
          <CorrectionAccordion
            corrections={filterPriorityCorrections(report.corrections, 'priority')}
            total={filterPriorityCorrections(report.corrections, 'priority').length}
          />
        </div>
      )}

      <CorrectionAccordion corrections={report.corrections} total={report.total_corrections} />
    </div>
  );
}
