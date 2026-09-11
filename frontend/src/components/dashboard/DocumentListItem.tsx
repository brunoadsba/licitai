'use client';

import Link from 'next/link';
import { FileText, Trash2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { Badge } from '@/components/ui/Badge';
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

export function statusCta(
  doc: DocumentResponse,
): { href: string; label: string; variant?: 'primary' | 'secondary' } | null {
  switch (doc.status) {
    case 'parsed':
      // Secondary: o primary da página é "Enviar TR"
      return { href: `/analysis/${doc.id}`, label: 'Analisar', variant: 'secondary' };
    case 'completed':
      return { href: `/analysis/${doc.id}`, label: 'Ver resultado', variant: 'secondary' };
    case 'parsing':
    case 'analyzing':
    case 'uploaded':
      return { href: `/analysis/${doc.id}`, label: 'Acompanhar', variant: 'secondary' };
    case 'error':
      return { href: `/analysis/${doc.id}`, label: 'Ver detalhes', variant: 'secondary' };
    default:
      return { href: `/analysis/${doc.id}`, label: 'Abrir', variant: 'secondary' };
  }
}

interface DocumentListItemProps {
  doc: DocumentResponse;
  onRequestDelete: (doc: DocumentResponse) => void;
}

export default function DocumentListItem({ doc, onRequestDelete }: DocumentListItemProps) {
  const cta = statusCta(doc);

  return (
    <motion.li
      variants={{
        hidden: { opacity: 0, y: 8 },
        show: { opacity: 1, y: 0 },
      }}
    >
      <Link
        href={`/analysis/${doc.id}`}
        className="block rounded-xl border border-line-subtle bg-surface/40 p-5 outline-none transition-colors hover:bg-surface-hover/50 focus-visible:ring-2 focus-visible:ring-accent-500/60"
      >
        <div className="flex flex-wrap items-center justify-between gap-4 sm:flex-nowrap">
          <div className="flex min-w-0 flex-1 items-center gap-4">
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
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-content-primary">
                {doc.filename_original}
              </p>
              <div className="tnum mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-content-muted">
                <span>{formatFileSize(doc.file_size_bytes)}</span>
                <span aria-hidden>·</span>
                <span>{doc.total_items} itens</span>
                {doc.status === 'completed' && doc.tokens_estimated ? (
                  <>
                    <span aria-hidden>·</span>
                    <span className="text-content-muted">
                      ~{doc.tokens_estimated.toLocaleString('pt-BR')} tokens
                    </span>
                  </>
                ) : null}
                <span aria-hidden>·</span>
                <span>{formatDate(doc.created_at)}</span>
              </div>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2.5">
            <Badge tone={STATUS_TONES[doc.status] ?? 'info'}>
              {STATUS_LABELS[doc.status] || doc.status}
            </Badge>
            {cta && (
              <span
                className={
                  cta.variant === 'secondary'
                    ? 'inline-flex h-8 items-center rounded-md border border-line-strong bg-white/[0.04] px-3 text-xs font-medium text-content-secondary'
                    : 'inline-flex h-8 items-center rounded-md bg-accent-700 px-3 text-xs font-medium text-white shadow-rim'
                }
              >
                {cta.label}
              </span>
            )}
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onRequestDelete(doc);
              }}
              className="rounded-lg p-2 text-content-subtle outline-none transition-colors hover:bg-red-500/10 hover:text-red-400 focus-visible:ring-2 focus-visible:ring-accent-500/60"
              aria-label={`Remover ${doc.filename_original}`}
            >
              <Trash2 className="h-4 w-4" aria-hidden />
            </button>
          </div>
        </div>
      </Link>
    </motion.li>
  );
}
