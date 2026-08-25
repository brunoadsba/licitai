'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, FileText, MessageSquareText, PenLine, Scale } from 'lucide-react';
import type { ChatCitation } from '@/types';

const TYPE_ICONS = {
  legal: Scale,
  analysis: MessageSquareText,
  correction: PenLine,
  document_item: FileText,
} as const;

export default function CitationList({ sources }: { sources: ChatCitation[] }) {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;

  const Chevron = open ? ChevronDown : ChevronRight;

  return (
    <div className="mt-2 border-t border-line-subtle pt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex items-center gap-1 text-[11px] text-accent-400/80 outline-none transition-colors hover:text-accent-300 focus-visible:ring-2 focus-visible:ring-accent-500/60"
      >
        <Chevron className="h-3 w-3" aria-hidden />
        Fontes citadas ({sources.length})
      </button>
      {open && (
        <ul className="mt-2 space-y-1.5">
          {sources.map((c, idx) => {
            const Icon = TYPE_ICONS[c.type as keyof typeof TYPE_ICONS] ?? FileText;
            return (
              <li
                key={`${c.type}-${c.reference}-${idx}`}
                className="rounded-lg bg-canvas/50 px-2.5 py-2 text-[11px]"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1 font-semibold text-content-muted">
                    <Icon className="h-3 w-3 shrink-0" aria-hidden />
                    {c.type === 'legal'
                      ? 'Lei'
                      : c.type === 'analysis'
                        ? 'Análise'
                        : c.type === 'correction'
                          ? 'Correção'
                          : c.type === 'document_item'
                            ? 'Item'
                            : c.type}
                  </span>
                  <span className="tnum truncate font-mono text-accent-400">{c.reference}</span>
                </div>
                {c.title && <p className="mt-0.5 truncate text-content-subtle">{c.title}</p>}
                {c.snippet && (
                  <p className="mt-0.5 line-clamp-2 text-content-subtle/80">{c.snippet}</p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
