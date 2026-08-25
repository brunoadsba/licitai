'use client';

import { Toaster as SonnerToaster } from 'sonner';

/** Toaster global do app — montar uma vez no layout raiz (DESIGN.md §5). */
export function Toaster() {
  return (
    <SonnerToaster
      theme="dark"
      position="bottom-right"
      toastOptions={{
        style: {
          background: '#171C25',
          border: '1px solid rgba(255,255,255,0.10)',
          color: '#F2F5F7',
        },
      }}
      mobileOffset="16px"
    />
  );
}
