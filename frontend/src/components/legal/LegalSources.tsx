'use client';

import { useEffect, useState } from 'react';
import { getLegalSources, type LegalSource } from '@/lib/api';
import { copy } from '@/lib/copy';

const FALLBACK: LegalSource[] = [
  {
    id: 'Lei 14.133/2021',
    label: 'Lei 14.133/2021',
    kind: 'lei',
    status: 'em_uso',
    searchable: true,
    search_law: '14.133',
  },
  {
    id: 'Lei 13.303/2016',
    label: 'Lei 13.303/2016',
    kind: 'lei',
    status: 'em_uso',
    searchable: true,
    search_law: '13.303',
  },
  {
    id: 'RILC CODEBA',
    label: 'RILC CODEBA',
    kind: 'regulamento',
    status: 'em_uso',
    searchable: true,
    search_law: 'RILC',
  },
  {
    id: 'tcu',
    label: 'TCU',
    kind: 'jurisprudencia',
    status: 'quarentena',
    searchable: false,
    search_law: null,
  },
];

function statusLabel(status: LegalSource['status']) {
  if (status === 'em_uso') return copy.legal.statusEmUso;
  if (status === 'nao_ingerido') return copy.legal.statusNaoIngerido;
  return copy.legal.statusQuarentena;
}

function sourceBlurb(id: string): string | undefined {
  const blurbs = copy.legal.sourceBlurb;
  return blurbs[id as keyof typeof blurbs];
}

export function LegalSources({
  onOpen,
}: {
  onOpen: (law: string) => void;
}) {
  const [sources, setSources] = useState<LegalSource[]>(FALLBACK);

  useEffect(() => {
    getLegalSources()
      .then(setSources)
      .catch(() => setSources(FALLBACK));
  }, []);

  return (
    <section aria-labelledby="fontes-piloto" className="glass-card space-y-3 p-5 sm:p-6">
      <header>
        <h2 id="fontes-piloto" className="text-sm font-medium text-content-primary">
          {copy.legal.sourcesTitle}
        </h2>
        <p className="mt-1 text-sm text-content-muted">{copy.legal.sourcesHint}</p>
      </header>
      <ul className="space-y-2">
        {sources.map((source) => {
          const blurb = sourceBlurb(source.id);
          return (
            <li
              key={source.id}
              className="flex items-start justify-between gap-x-6 gap-y-2 rounded-lg border border-line-subtle px-4 py-3"
            >
              <div className="min-w-0 flex-1">
                {source.searchable && source.search_law ? (
                  <button
                    type="button"
                    onClick={() => onOpen(source.search_law as string)}
                    className="text-left text-sm font-medium text-content-primary outline-none hover:underline focus-visible:ring-2 focus-visible:ring-accent-500/60"
                  >
                    {source.label}
                  </button>
                ) : (
                  <span className="text-sm font-medium text-content-primary">{source.label}</span>
                )}
                {blurb ? (
                  <p className="mt-1 text-sm leading-snug text-content-muted">{blurb}</p>
                ) : null}
                {source.id === 'tcu' && source.status === 'quarentena' ? (
                  <p className="mt-1 text-sm leading-snug text-content-muted">
                    {copy.legal.tcuWhy}
                  </p>
                ) : null}
              </div>
              <span className="shrink-0 pt-0.5 text-xs text-content-muted">
                {statusLabel(source.status)}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
