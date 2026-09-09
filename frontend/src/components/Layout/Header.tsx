'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Menu, ShieldCheck, ShieldAlert, ShieldQuestion } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useShell } from './ShellContext';

const BREADCRUMB_MAP: Record<string, string> = {
  '/': 'Painel',
  '/upload': 'Enviar Documento',
  '/wizard': 'Enviar Documento',
  '/gerar-tr': 'Gerar TR',
  '/analysis': 'Análise',
  '/report': 'Relatório',
  '/comparacao': 'Comparações',
  '/comparacao/versoes': 'Versões de TR',
  '/comparacao/matriz': 'Matriz de Conformidade',
  '/moldes': 'Moldes de Regras',
  '/design': 'Design System',
};

type BackendStatus = 'checking' | 'online' | 'offline';

function useBackendStatus(): BackendStatus {
  const [status, setStatus] = useState<BackendStatus>('checking');

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function probe() {
      try {
        const res = await fetch('/readyz', { signal: AbortSignal.timeout(5000) });
        if (!cancelled) setStatus(res.ok ? 'online' : 'offline');
      } catch {
        if (!cancelled) setStatus('offline');
      }
      if (!cancelled) timer = setTimeout(probe, 30_000);
    }

    probe();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  return status;
}

const STATUS_CONFIG: Record<
  BackendStatus,
  { label: string; icon: typeof ShieldCheck; className: string }
> = {
  checking: { label: 'Verificando…', icon: ShieldQuestion, className: 'text-content-subtle' },
  online: { label: 'Sistema ativo', icon: ShieldCheck, className: 'text-green-400' },
  offline: { label: 'Sistema indisponível', icon: ShieldAlert, className: 'text-red-400' },
};

function Breadcrumb({ pathname }: { pathname: string }) {
  const parts = pathname.split('/').filter(Boolean);

  if (parts.length === 0) {
    return <span className="text-content-muted">SEI</span>;
  }

  const crumbs = parts.map((part, i) => {
    const path = '/' + parts.slice(0, i + 1).join('/');
    const label =
      BREADCRUMB_MAP[path] ??
      (/^[\w-]{8,}$/.test(part) ? 'Detalhe' : decodeURIComponent(part));
    return { path, label, last: i === parts.length - 1 };
  });

  return (
    <nav
      aria-label="Trilha de navegação"
      className="flex items-center gap-1.5 text-xs text-content-subtle"
    >
      <Link
        href="/"
        className="outline-none transition-colors hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
      >
        Painel
      </Link>
      {crumbs.map((c) => (
        <span key={c.path} className="flex items-center gap-1.5">
          <span aria-hidden>/</span>
          {c.last ? (
            <span className="text-content-muted">{c.label}</span>
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

export default function Header() {
  const pathname = usePathname();
  const { openSidebar } = useShell();
  const status = useBackendStatus();
  const statusConfig = STATUS_CONFIG[status];
  const StatusIcon = statusConfig.icon;

  const parts = pathname.split('/').filter(Boolean);
  const title = BREADCRUMB_MAP[pathname] ?? BREADCRUMB_MAP['/' + (parts[0] ?? '')] ?? 'Painel';

  return (
    <header className="sticky top-0 z-30 border-b border-line-subtle bg-panel/80 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <button
            onClick={openSidebar}
            aria-label="Abrir menu de navegação"
            className="rounded-lg p-2 text-content-muted outline-none transition-colors hover:bg-white/[0.06] hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60 lg:hidden"
          >
            <Menu className="h-5 w-5" aria-hidden />
          </button>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo-codeba.png"
            alt="CODEBA"
            width={90}
            height={24}
            className="h-6 w-auto rounded bg-white px-1.5 py-0.5 object-contain lg:hidden"
          />
          <div className="min-w-0">
            <Breadcrumb pathname={pathname} />
            <h2 className="truncate text-base font-semibold tracking-tight text-content-primary sm:text-lg">
              {title}
            </h2>
          </div>
        </div>

        <div
          className="flex shrink-0 items-center gap-2 rounded-lg border border-line-subtle bg-white/[0.03] px-3 py-1.5"
          title="Disponibilidade do serviço verificada a cada 30s"
        >
          <StatusIcon className={cn('h-3.5 w-3.5', statusConfig.className)} aria-hidden />
          <span className="text-xs text-content-muted">{statusConfig.label}</span>
        </div>
      </div>
    </header>
  );
}
