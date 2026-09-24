'use client';

import { FormEvent, Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getLegalProvisions, type LegalProvision } from '@/lib/api';
import { Button } from '@/components/ui/Button';

export default function LegalProvisionPage() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-content-muted">Carregando dispositivo…</p>}>
      <LegalProvisionSearch />
    </Suspense>
  );
}

function LegalProvisionSearch() {
  const params = useSearchParams();
  const router = useRouter();
  const [rows, setRows] = useState<LegalProvision[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const law = params.get('law') || params.get('law_number') || '';
  const article = params.get('article') || '';
  const path = params.get('path') || '';

  useEffect(() => {
    if (!law && !article && !path) {
      setRows([]);
      setError(null);
      return;
    }
    setLoading(true);
    getLegalProvisions({
      law_number: law || undefined,
      article: article || undefined,
      path: path || undefined,
    })
      .then((data) => {
        setRows(data);
        setError(null);
      })
      .catch(() => setError('Não foi possível carregar o dispositivo.'))
      .finally(() => setLoading(false));
  }, [law, article, path]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const nextLaw = String(form.get('law') || '').trim();
    const nextArticle = String(form.get('article') || '').trim();
    const query = new URLSearchParams();
    if (nextLaw) query.set('law', nextLaw);
    if (nextArticle) query.set('article', nextArticle);
    router.push(query.toString() ? `/legal?${query}` : '/legal');
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <h1 className="text-xl font-semibold text-content-primary">Dispositivo jurídico</h1>
      <p className="text-sm text-content-muted">
        Consulte o texto vigente (lei e artigo). O índice versionado cobre a amostra
        14.133/13.303.
      </p>
      <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-3">
        <label className="grid gap-1 text-xs text-content-muted">
          Lei
          <input
            name="law"
            defaultValue={law}
            placeholder="14.133"
            className="h-10 rounded-lg border border-line-strong bg-transparent px-3 text-sm text-content-primary"
          />
        </label>
        <label className="grid gap-1 text-xs text-content-muted">
          Artigo
          <input
            name="article"
            defaultValue={article}
            placeholder="Art. 6º"
            className="h-10 rounded-lg border border-line-strong bg-transparent px-3 text-sm text-content-primary"
          />
        </label>
        <Button type="submit">Buscar</Button>
      </form>
      {loading && <p className="text-sm text-content-muted">Buscando…</p>}
      {error && <p className="text-sm text-red-400">{error}</p>}
      {!loading && !error && !law && !article && !path && (
        <p className="text-sm text-content-muted">Informe a lei ou o artigo para buscar.</p>
      )}
      {!loading && !error && (law || article || path) && rows.length === 0 && (
        <p className="text-sm text-content-muted">Nenhum dispositivo vigente encontrado.</p>
      )}
      {rows.map((row) => (
        <article key={row.id} className="rounded-lg border border-line-subtle bg-surface/50 p-4">
          <p className="text-xs text-content-muted">
            {row.law_number} · {row.path} · {row.status} · versão {row.version_status}
          </p>
          <h2 className="mt-1 text-sm font-semibold text-content-primary">{row.law_title}</h2>
          {row.ancestors.map((item) => (
            <p key={item.path} className="mt-2 text-sm text-content-secondary">
              {item.text}
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
