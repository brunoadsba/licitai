'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { FileText, FileUp, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { motion, MotionConfig } from 'framer-motion';
import {
  deleteDocument,
  getMetricsSnapshot,
  getPendingSummary,
  listDocuments,
  type MetricsSnapshot,
  type PendingSummaryResponse,
} from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import DocumentListItem from '@/components/dashboard/DocumentListItem';
import { PendingReviewList, PilotHealthPanel } from '@/components/dashboard/PilotSignals';
import type { DocumentResponse } from '@/types';

export default function DashboardClient({
  initialDocuments,
  initialError,
}: {
  initialDocuments: DocumentResponse[];
  initialError: string | null;
}) {
  const [documents, setDocuments] = useState<DocumentResponse[]>(initialDocuments);
  const [error, setError] = useState<string | null>(initialError);
  const [confirmDelete, setConfirmDelete] = useState<DocumentResponse | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [pending, setPending] = useState<PendingSummaryResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null);
  const [healthOpen, setHealthOpen] = useState(false);

  const errorInfo = error ? getErrorMessage(error, 'documents') : null;
  const hasInFlight = documents.some(
    (d) => d.status === 'parsing' || d.status === 'analyzing' || d.status === 'uploaded',
  );

  async function loadPilotSignals() {
    try {
      const [p, m] = await Promise.all([
        getPendingSummary().catch(() => null),
        getMetricsSnapshot().catch(() => null),
      ]);
      if (p) setPending(p);
      if (m) setMetrics(m);
    } catch {
      /* painel piloto opcional */
    }
  }

  async function handleRefresh() {
    try {
      setRefreshing(true);
      const data = await listDocuments();
      setDocuments(data.documents);
      setError(null);
      await loadPilotSignals();
    } catch {
      setError('Não foi possível carregar os documentos. Atualize a página ou tente novamente.');
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadPilotSignals();
  }, []);

  useEffect(() => {
    if (!hasInFlight) return;
    const id = window.setInterval(() => {
      void handleRefresh();
    }, 8000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasInFlight]);

  async function handleDelete(id: string) {
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      toast.success('Documento removido');
    } catch {
      toast.error('Não foi possível remover o documento');
    }
  }

  const stats = [
    { label: 'Total', value: documents.length },
    {
      label: 'Em análise',
      value: documents.filter((d) => d.status === 'analyzing' || d.status === 'parsing').length,
    },
    { label: 'Concluídos', value: documents.filter((d) => d.status === 'completed').length },
    {
      label: 'Aguardando revisão',
      value: pending?.total ?? 0,
    },
  ];

  const showLoading = refreshing && documents.length === 0;

  return (
    <div className="animate-fade-in space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-content-primary">
            Revisar Termos de Referência
          </h1>
          <p className="mt-1 max-w-xl text-sm text-content-muted">
            IA sugere; você decide. Só correções aprovadas ou ajustadas vão para o SEI.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            loading={refreshing}
            onClick={() => void handleRefresh()}
            aria-label="Atualizar lista de documentos"
          >
            <RefreshCw className="h-4 w-4" aria-hidden />
            Atualizar
          </Button>
          {!(documents.length === 0 && !error) && (
            <>
              <Link href="/comparacao/versoes">
                <Button size="sm" variant="secondary">
                  Atualizar TR
                </Button>
              </Link>
              <Link href="/upload">
                <Button>
                  <FileUp className="h-4 w-4" aria-hidden />
                  Enviar e revisar TR
                </Button>
              </Link>
            </>
          )}
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="glass-card p-5">
            <dt className="text-[11px] uppercase tracking-widest text-content-subtle">
              {stat.label}
            </dt>
            <dd className="tnum mt-1 text-3xl font-semibold tracking-tight text-content-primary">
              {stat.value}
            </dd>
          </div>
        ))}
      </dl>

      {pending && pending.items.length > 0 && <PendingReviewList pending={pending} />}

      <PilotHealthPanel
        metrics={metrics}
        open={healthOpen}
        onToggle={() => setHealthOpen((v) => !v)}
      />

      {errorInfo && (
        <AlertBanner variant="error" title={errorInfo.title}>
          {errorInfo.message}
        </AlertBanner>
      )}

      <div aria-live="polite">
        {showLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="glass-card">
            <EmptyState
              icon={FileText}
              title="Nenhum TR ainda"
              description="Envie um Termo de Referência para revisar achados prioritários e copiar o aprovado para o SEI."
              action={
                <Link href="/upload">
                  <Button>
                    <FileUp className="h-4 w-4" aria-hidden />
                    Enviar e revisar TR
                  </Button>
                </Link>
              }
            />
          </div>
        ) : (
          <MotionConfig reducedMotion="user">
            <motion.ul
              className="space-y-3"
              initial="hidden"
              animate="show"
              variants={{ hidden: {}, show: { transition: { staggerChildren: 0.04 } } }}
            >
              {documents.map((doc) => (
                <DocumentListItem
                  key={doc.id}
                  doc={doc}
                  onRequestDelete={setConfirmDelete}
                />
              ))}
            </motion.ul>
          </MotionConfig>
        )}
      </div>

      <ConfirmDialog
        open={confirmDelete !== null}
        title="Remover documento"
        message={`Remover "${confirmDelete?.filename_original}"? Esta ação não pode ser desfeita.`}
        confirmLabel="Remover"
        danger
        onConfirm={() => {
          if (confirmDelete) handleDelete(confirmDelete.id);
          setConfirmDelete(null);
        }}
        onCancel={() => setConfirmDelete(null)}
      />
    </div>
  );
}
