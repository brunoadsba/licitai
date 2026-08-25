'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { FileText, FileUp, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { motion, MotionConfig } from 'framer-motion';
import { listDocuments, deleteDocument } from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import type { DocumentResponse } from '@/types';
import { STATUS_LABELS } from '@/types';

const STATUS_TONES: Record<string, 'info' | 'medium' | 'low' | 'critical'> = {
  uploaded: 'info',
  parsing: 'medium',
  parsed: 'medium',
  analyzing: 'medium',
  completed: 'low',
  error: 'critical',
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function DashboardPage() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<DocumentResponse | null>(null);

  const errorInfo = error ? getErrorMessage(error, 'documents') : null;

  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    try {
      setLoading(true);
      const data = await listDocuments();
      setDocuments(data.documents);
    } catch {
      setError('Erro ao carregar documentos. Verifique se o backend está rodando.');
    } finally {
      setLoading(false);
    }
  }

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
    { label: 'Analisados', value: documents.filter((d) => d.status === 'completed').length },
    { label: 'Pendentes', value: documents.filter((d) => d.status === 'parsed').length },
    { label: 'Erros', value: documents.filter((d) => d.status === 'error').length },
  ];

  return (
    <div className="animate-fade-in space-y-8">
      {/* Cabeçalho */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-content-primary">
            Seus Documentos
          </h1>
          <p className="mt-1 text-sm text-content-muted">
            Gerencie e analise seus Termos de Referência
          </p>
        </div>
        <Link href="/upload">
          <Button>
            <FileUp className="h-4 w-4" aria-hidden />
            Enviar Documento
          </Button>
        </Link>
      </div>

      {/* Estatísticas rápidas */}
      <dl className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="glass-card p-5">
            <dt className="text-[11px] uppercase tracking-widest text-content-subtle">
              {stat.label}
            </dt>
            <dd className="tnum mt-1 text-3xl font-semibold tracking-tight text-content-primary">
              {loading ? '—' : stat.value}
            </dd>
          </div>
        ))}
      </dl>

      {/* Mensagem de erro */}
      {errorInfo && (
        <AlertBanner variant="error" title={errorInfo.title}>
          {errorInfo.message}
        </AlertBanner>
      )}

      {/* Lista de documentos */}
      <div aria-live="polite">
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="glass-card">
            <EmptyState
              icon={FileText}
              title="Nenhum documento"
              description="Envie seu primeiro Termo de Referência para começar a análise."
              action={
                <Link href="/upload">
                  <Button>
                    <FileUp className="h-4 w-4" aria-hidden />
                    Enviar Documento
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
                <motion.li
                  key={doc.id}
                  variants={{
                    hidden: { opacity: 0, y: 8 },
                    show: { opacity: 1, y: 0 },
                  }}
                  className="glass-card-interactive p-5"
                >
                <div className="flex flex-wrap items-center justify-between gap-4 sm:flex-nowrap">
                  <div className="flex min-w-0 flex-1 items-center gap-4">
                    {/* Ícone do tipo */}
                    <div
                      className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border ${
                        doc.file_type === 'pdf'
                          ? 'border-red-500/20 bg-red-500/10 text-red-400'
                          : 'border-sky-500/20 bg-sky-500/10 text-sky-400'
                      }`}
                      aria-hidden
                    >
                      <FileText className="h-5 w-5" strokeWidth={1.5} />
                    </div>

                    {/* Info */}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-content-primary">
                        {doc.filename_original}
                      </p>
                      <div className="tnum mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-content-subtle">
                        <span>{formatFileSize(doc.file_size_bytes)}</span>
                        <span aria-hidden>·</span>
                        <span>{doc.total_items} itens</span>
                        <span aria-hidden>·</span>
                        <span>{formatDate(doc.created_at)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Ações */}
                  <div className="flex shrink-0 items-center gap-2.5">
                    <Badge tone={STATUS_TONES[doc.status] ?? 'info'}>
                      {STATUS_LABELS[doc.status] || doc.status}
                    </Badge>

                    {doc.status === 'parsed' && (
                      <Link href={`/analysis/${doc.id}`}>
                        <Button size="sm">Analisar</Button>
                      </Link>
                    )}

                    {doc.status === 'completed' && (
                      <Link href={`/analysis/${doc.id}`}>
                        <Button size="sm" variant="secondary">
                          Ver Resultado
                        </Button>
                      </Link>
                    )}

                    <button
                      onClick={() => setConfirmDelete(doc)}
                      className="rounded-lg p-2 text-content-subtle outline-none transition-colors hover:bg-red-500/10 hover:text-red-400 focus-visible:ring-2 focus-visible:ring-accent-500/60"
                      aria-label={`Remover ${doc.filename_original}`}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </button>
                  </div>
                </div>
                </motion.li>
              ))}
            </motion.ul>
          </MotionConfig>
        )}
      </div>

      {/* Confirmação de exclusão */}
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
