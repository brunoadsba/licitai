'use client';

import { useState } from 'react';
import type { ChatCitation } from '@/types';

const TYPE_LABELS: Record<string, string> = {
  legal: '⚖️ Lei',
  analysis: '📊 Análise',
  correction: '✍️ Correção',
  document_item: '📄 Item',
};

export default function CitationList({ sources }: { sources: ChatCitation[] }) {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-2 border-t border-white/[0.06] pt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-[11px] text-primary-400/80 hover:text-primary-300 flex items-center gap-1 transition-colors"
      >
        <span>{open ? '▾' : '▸'}</span>
        Fontes citadas ({sources.length})
      </button>
      {open && (
        <ul className="mt-2 space-y-1.5">
          {sources.map((c, idx) => (
            <li
              key={`${c.type}-${c.reference}-${idx}`}
              className="bg-surface-900/40 rounded-lg px-2.5 py-2 text-[11px]"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-gray-400 font-semibold truncate">
                  {TYPE_LABELS[c.type] || c.type}
                </span>
                <span className="text-primary-400 font-mono truncate">
                  {c.reference}
                </span>
              </div>
              {c.title && (
                <p className="text-gray-500 mt-0.5 truncate">{c.title}</p>
              )}
              {c.snippet && (
                <p className="text-gray-600 mt-0.5 line-clamp-2">{c.snippet}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
