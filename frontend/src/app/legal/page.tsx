'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { getLegalProvisions, type LegalProvision } from '@/lib/api';

export default function LegalProvisionPage() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-content-muted">Carregando dispositivo…</p>}>
      <LegalProvisionSearch />
    </Suspense>
  );
}

function LegalProvisionSearch() {
  const params = useSearchParams();
  const [rows, setRows] = useState<LegalProvision[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const law = params.get('law') || params.get('law_number') || undefined;
    const article = params.get('article') || undefined;
    const path = params.get('path') || undefined;
    getLegalProvisions({ law_number: law, article, path })
      .then(setRows)
      .catch(() => setError('Não foi possível carregar o dispositivo.'));
  }, [params]);

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <h1 className="text-xl font-semibold text-content-primary">Dispositivo jurídico</h1>
      {error && <p className="text-sm text-red-400">{error}</p>}
      {rows.length === 0 && !error && (
        <p className="text-sm text-content-muted">Nenhum dispositivo vigente encontrado.</p>
      )}
      {rows.map((row) => (
        <article key={row.id} className="rounded-lg border border-line-subtle bg-surface/50 p-4">
          <p className="text-xs text-content-muted">
            {row.law_number} · {row.path} · {row.status} · versão {row.version_status}
          </p>
          <h2 className="mt-1 text-sm font-semibold text-content-primary">{row.law_title}</h2>
          {row.ancestors.map((a) => (
            <p key={a.path} className="mt-2 text-sm text-content-secondary">
              {a.text}
            </p>
          ))}
          <p className="mt-3 whitespace-pre-wrap text-sm text-content-secondary">
            {row.canonical_text}
          </p>
          {row.source_url && (
            <a
              href={row.source_url}
              target="_blank"
              rel="noreferrer"
              className="mt-3 block text-xs text-accent-400 hover:underline"
            >
              Fonte oficial
            </a>
          )}
        </article>
      ))}
    </div>
  );
}
