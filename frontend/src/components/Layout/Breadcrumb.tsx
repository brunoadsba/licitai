'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { copy } from '@/lib/copy';

const BREADCRUMB_MAP: Record<string, string> = {
  '/': copy.nav.painel,
  '/upload': copy.nav.enviarTr,
  '/wizard': copy.nav.enviarTr,
  '/gerar-tr': 'Gerar TR',
  '/analysis': 'Análise',
  '/report': 'Relatório',
  '/comparacao': 'Comparações',
  '/comparacao/versoes': 'Versões de TR',
  '/moldes': 'Moldes',
  '/guia': copy.nav.comoUsar,
  '/complementos': copy.nav.complementos,
  '/legal': copy.nav.consultarLei,
  '/design': 'Design System',
};

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function buildCrumbs(pathname: string) {
  const parts = pathname.split('/').filter(Boolean);
  const crumbs = parts
    .map((part, i) => {
      const path = '/' + parts.slice(0, i + 1).join('/');
      if (UUID.test(part)) return null;
      const label = BREADCRUMB_MAP[path] ?? decodeURIComponent(part);
      return { path, label, last: i === parts.length - 1 };
    })
    .filter((c): c is { path: string; label: string; last: boolean } => c !== null);

  const isComplemento =
    pathname !== '/complementos' &&
    (pathname.startsWith('/gerar-tr') ||
      pathname.startsWith('/comparacao') ||
      pathname.startsWith('/moldes') ||
      pathname.startsWith('/legal'));
  if (isComplemento) {
    crumbs.unshift({
      path: '/complementos',
      label: copy.nav.complementos,
      last: false,
    });
  }

  if (crumbs.length === 1) {
    crumbs[0] = { ...crumbs[0], last: true };
  }
  return crumbs;
}

export function Breadcrumb() {
  const pathname = usePathname();
  if (pathname === '/') return null;

  const crumbs = buildCrumbs(pathname);
  if (crumbs.length === 0) return null;

  return (
    <nav
      aria-label="Trilha de navegação"
      className="no-print mb-4 flex flex-wrap items-center gap-1.5 text-sm text-content-muted"
    >
      <Link
        href="/"
        className="outline-none transition-colors hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
      >
        {copy.nav.painel}
      </Link>
      {crumbs.map((c) => (
        <span key={c.path} className="flex items-center gap-1.5">
          <span aria-hidden>/</span>
          {c.last ? (
            <span className="text-content-secondary">{c.label}</span>
          ) : (
            <Link
              href={c.path}
              className="outline-none transition-colors hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
            >
              {c.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}
