'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/components/theme/ThemeProvider';
import { cn } from '@/lib/utils';

/** Alterna claro/escuro — persiste em localStorage. */
export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? 'Ativar tema claro' : 'Ativar tema escuro'}
      title={isDark ? 'Tema claro' : 'Tema escuro'}
      className={cn(
        'inline-flex h-9 w-9 items-center justify-center rounded-full border border-line-subtle',
        'text-content-muted shadow-rim outline-none transition-colors',
        'hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60',
        'focus-visible:ring-offset-2 focus-visible:ring-offset-canvas',
        className,
      )}
      style={{ backgroundColor: 'var(--overlay-hover)' }}
    >
      {isDark ? (
        <Sun className="h-4 w-4" strokeWidth={1.75} aria-hidden />
      ) : (
        <Moon className="h-4 w-4" strokeWidth={1.75} aria-hidden />
      )}
    </button>
  );
}
