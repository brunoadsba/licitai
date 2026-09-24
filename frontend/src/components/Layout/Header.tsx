'use client';

import { useEffect, useState } from 'react';
import { Menu, ShieldAlert } from 'lucide-react';
import { useShell } from './ShellContext';
import { ThemeToggle } from '@/components/theme/ThemeToggle';
import { copy } from '@/lib/copy';

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

export default function Header() {
  const { openSidebar, desktopNavHidden, showDesktopNav } = useShell();
  const status = useBackendStatus();

  return (
    <header className="sticky top-0 z-30 border-b border-line-subtle bg-panel/70 backdrop-blur-2xl">
      <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={openSidebar}
            aria-label="Abrir menu de navegação"
            className="rounded-lg p-2 text-content-muted outline-none transition-colors hover:bg-white/[0.06] hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60 lg:hidden"
          >
            <Menu className="h-5 w-5" aria-hidden />
          </button>
          {desktopNavHidden && (
            <button
              type="button"
              onClick={showDesktopNav}
              aria-label="Mostrar menu lateral"
              title="Mostrar menu"
              className="hidden rounded-lg p-2 text-content-muted outline-none transition-colors hover:bg-white/[0.06] hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60 lg:inline-flex"
            >
              <Menu className="h-5 w-5" aria-hidden />
            </button>
          )}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo.svg"
            alt="LicitAI"
            width={90}
            height={28}
            className="h-6 w-auto object-contain"
          />
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <ThemeToggle />
          {status === 'offline' && (
            <div
              className="flex items-center gap-2 rounded-full border border-red-500/30 bg-red-500/10 px-3 py-1.5"
              title={copy.header.offline}
            >
              <ShieldAlert className="h-3.5 w-3.5 text-red-400" aria-hidden />
              <span className="text-xs text-content-muted">{copy.header.offline}</span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
