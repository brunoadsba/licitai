'use client';

import Link from 'next/link';
import { FileText, MoreHorizontal, Trash2 } from 'lucide-react';
import { motion } from 'framer-motion';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/DropdownMenu';
import type { DocumentResponse } from '@/types';
import { copy } from '@/lib/copy';

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
  pendingPriority = 0,
): { href: string; label: string } {
  switch (doc.status) {
    case 'parsed':
      return { href: `/analysis/${doc.id}`, label: copy.cta.analisar };
    case 'completed':
      return {
        href: `/analysis/${doc.id}`,
        label: pendingPriority > 0 ? copy.cta.revisar : copy.cta.abrir,
      };
    case 'parsing':
    case 'analyzing':
    case 'uploaded':
      return { href: `/analysis/${doc.id}`, label: copy.cta.acompanhar };
    default:
      return { href: `/analysis/${doc.id}`, label: copy.cta.abrir };
  }
}

interface DocumentListItemProps {
  doc: DocumentResponse;
  pendingPriority?: number;
  onRequestDelete: (doc: DocumentResponse) => void;
}

export default function DocumentListItem({
  doc,
  pendingPriority = 0,
  onRequestDelete,
}: DocumentListItemProps) {
  const cta = statusCta(doc, pendingPriority);

  return (
    <motion.li
      variants={{
        hidden: { opacity: 0, y: 8 },
        show: { opacity: 1, y: 0 },
      }}
    >
      <Link
        href={cta.href}
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
              <p className="tnum mt-1 text-xs text-content-muted">{formatDate(doc.created_at)}</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="inline-flex h-8 items-center rounded-md border border-line-strong bg-white/[0.04] px-3 text-xs font-medium text-content-secondary">
              {cta.label}
            </span>
            <div
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
              }}
            >
              <DropdownMenu>
                <DropdownMenuTrigger
                  className="rounded-lg p-2 text-content-subtle outline-none transition-colors hover:bg-white/[0.06] hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
                  aria-label={`${copy.dashboard.more} ${doc.filename_original}`}
                >
                  <MoreHorizontal className="h-4 w-4" aria-hidden />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    destructive
                    onSelect={() => onRequestDelete(doc)}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                    {copy.dashboard.remove}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>
      </Link>
    </motion.li>
  );
}
