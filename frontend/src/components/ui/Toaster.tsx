'use client';

import { Toaster as SonnerToaster } from 'sonner';
import { useTheme } from '@/components/theme/ThemeProvider';

/** Toaster global — acompanha tema claro/escuro. */
export function Toaster() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <SonnerToaster
      theme={isDark ? 'dark' : 'light'}
      position="bottom-right"
      toastOptions={{
        style: isDark
          ? {
              background: '#111827',
              border: '1px solid rgba(148,163,184,0.16)',
              color: '#F1F5F9',
            }
          : {
              background: '#ffffff',
              border: '1px solid rgba(15,23,42,0.12)',
              color: '#0F172A',
            },
      }}
      mobileOffset="16px"
    />
  );
}
