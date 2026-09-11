'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { BookOpen, FileText, FileUp, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { motion, MotionConfig } from 'framer-motion';
import {
  getPendingSummary,
  listDocuments,
  deleteDocument,
  type PendingSummaryResponse,
} from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import DocumentListItem from '@/components/dashboard/DocumentListItem';
import { PendingReviewList } from '@/components/dashboard/PilotSignals';
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

  const errorInfo = error ? getErrorMessage(error, 'documents') : null;
  const hasInFlight = documents.some(
    (d) => d.status === 'parsing' || d.status === 'analyzing' || d.status === 'uploaded',
  );

  async function loadPending() {
    try {
      const p = await getPendingSummary().catch(() => null);
      if (p) setPending(p);
    } catch {
      /* pendências opcionais */
    }
  }

  async function handleRefresh() {
    try {
      setRefreshing(true);
      const data = await listDocuments();
      setDocuments(data.documents);
      setError(null);
      await loadPending();
    } catch {
      setError('Não foi possível carregar os documentos. Atualize a página ou tente novamente.');
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadPending();
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

  const awaitingReview = pending?.total ?? 0;
  const inFlight = documents.filter(
    (d) => d.status === 'analyzing' || d.status === 'parsing',
  ).length;
  const nextToReview = pending?.items?.[0];
  const showLoading = refreshing && documents.length === 0;
  /** Hero só quando há ação/status real — evita CTA duplicado com o header. */
  const showHero = awaitingReview > 0 || inFlight > 0;

  return (
    <div className="animate-fade-in space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-content-primary">
            Revisar Termos de Referência
          </h1>
          <p className="mt-1 max-w-xl text-sm text-content-muted">
            {awaitingReview > 0
              ? `${awaitingReview} correção(ões) aguardando sua decisão.`
              : 'Envie um TR, revise os achados e copie só o aprovado para o SEI.'}
          </p>
          <Link
            href="/guia"
            className="mt-2 inline-flex items-center gap-1.5 text-xs text-content-subtle outline-none hover:text-accent-400 focus-visible:ring-2 focus-visible:ring-accent-500/60"
          >
            <BookOpen className="h-3.5 w-3.5" aria-hidden />
            Guia do usuário
          </Link>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {(hasInFlight || refreshing) && (
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
          )}
          {!(documents.length === 0 && !error) && (
            <Link href="/upload">
              <Button>
                <FileUp className="h-4 w-4" aria-hidden />
                Enviar TR
              </Button>
            </Link>
          )}
        </div>
      </div>

      {showHero && (
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-accent-500/25 bg-accent-500/5 p-5">
          <div>
            <p className="text-sm font-medium text-content-primary">
              {awaitingReview > 0
                ? 'Há revisões pendentes'
                : `${inFlight} análise(s) em andamento`}
            </p>
            <p className="mt-0.5 text-xs text-content-muted">
              {nextToReview
                ? `Próximo: ${nextToReview.filename}`
                : 'A lista atualiza automaticamente.'}
            </p>
          </div>
          {nextToReview?.document_id ? (
            <Link href={`/analysis/${nextToReview.document_id}`}>
              <Button size="sm">Continuar revisão</Button>
            </Link>
          ) : (
            <Button
              size="sm"
              variant="secondary"
              loading={refreshing}
              onClick={() => void handleRefresh()}
            >
              <RefreshCw className="h-4 w-4" aria-hidden />
              Atualizar
            </Button>
          )}
        </div>
      )}

      {pending && pending.items.length > 0 && <PendingReviewList pending={pending} />}

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
          <div className="rounded-lg border border-line-subtle bg-surface/30">
            <EmptyState
              icon={FileText}
              title="Nenhum TR ainda"
              description="Envie um Termo de Referência para revisar achados e copiar o aprovado para o SEI."
              action={
                <Link href="/upload">
                  <Button>
                    <FileUp className="h-4 w-4" aria-hidden />
                    Enviar TR
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
