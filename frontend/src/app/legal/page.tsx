'use client';

import { FormEvent, Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getLegalProvisions, type LegalProvision } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { LegalSources } from '@/components/legal/LegalSources';
import { copy } from '@/lib/copy';

export default function LegalProvisionPage() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-content-muted">{copy.legal.loading}</p>}>
      <LegalProvisionSearch />
    </Suspense>
  );
}

function hrefFor(law: string, article: string) {
  const query = new URLSearchParams();
  if (law) query.set('law', law);
  if (article) query.set('article', article);
  return query.toString() ? `/legal?${query}` : '/legal';
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
  const idle = !law && !article && !path;

  useEffect(() => {
    if (idle) {
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
      .catch(() => setError(copy.legal.error))
      .finally(() => setLoading(false));
  }, [law, article, path, idle]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const nextLaw = String(form.get('law') || '').trim();
    const nextArticle = String(form.get('article') || '').trim();
    router.push(hrefFor(nextLaw, nextArticle));
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-content-primary">
          {copy.legal.title}
        </h1>
        <p className="mt-1 text-sm text-content-muted">
          Consulte o texto ingerido neste piloto.
        </p>
      </header>

      <LegalSources onOpen={(nextLaw) => router.push(hrefFor(nextLaw, ''))} />

      <div className="glass-card space-y-5 p-5 sm:p-6">
        <form
          key={`${law}|${article}`}
          onSubmit={onSubmit}
          className="flex flex-wrap items-end gap-3"
        >
          <label className="grid min-w-[8rem] flex-1 gap-1 text-xs text-content-muted">
            Lei
            <input
              name="law"
              defaultValue={law}
              placeholder="14.133"
              className="input-field h-10 w-full text-sm"
            />
          </label>
          <label className="grid min-w-[8rem] flex-1 gap-1 text-xs text-content-muted">
            Artigo
            <input
              name="article"
              defaultValue={article}
              placeholder="Art. 6º"
              className="input-field h-10 w-full text-sm"
            />
          </label>
          <Button type="submit" className="shrink-0">
            Buscar
          </Button>
        </form>

        {idle && (
          <div>
            <p className="text-sm text-content-muted">{copy.legal.empty}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {copy.legal.shortcuts.map((item) => (
                <Button
                  key={item.label}
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => router.push(hrefFor(item.law, item.article))}
                >
                  {item.label}
                </Button>
              ))}
            </div>
          </div>
        )}

        {loading && <p className="text-sm text-content-muted">Buscando…</p>}
        {error && <p className="text-sm text-red-400">{error}</p>}
        {!loading && !error && !idle && rows.length === 0 && (
          <p className="text-sm text-content-muted">{copy.legal.none}</p>
        )}
      </div>

      {rows.map((row) => (
        <article key={row.id} className="glass-card p-5 sm:p-6">
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
