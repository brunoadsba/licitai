'use client';

import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import Sidebar from '@/components/Layout/Sidebar';
import Header from '@/components/Layout/Header';
import { Toaster } from '@/components/ui/Toaster';
import { useShell } from './ShellContext';

export function AppShell({ children }: { children: ReactNode }) {
  const { desktopNavHidden } = useShell();

  return (
    <>
      <div className="no-print">
        <Sidebar />
      </div>

      <div
        className={cn(
          'flex flex-1 flex-col transition-[padding] duration-200 ease-out',
          !desktopNavHidden && 'lg:pl-64',
        )}
      >
        <div className="no-print">
          <Header />
        </div>
        <main
          id="conteudo-principal"
          className="mx-auto w-full max-w-[1440px] flex-1 p-4 sm:p-6 lg:p-8 print:max-w-none print:p-0"
        >
          {children}
        </main>
      </div>

      <div className="no-print">
        <Toaster />
      </div>
    </>
  );
}
