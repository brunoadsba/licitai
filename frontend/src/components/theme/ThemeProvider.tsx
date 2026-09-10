'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type ThemeMode = 'light' | 'dark';

export const THEME_STORAGE_KEY = 'licitai-theme';

type ThemeContextValue = {
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function applyThemeClass(theme: ThemeMode) {
  const root = document.documentElement;
  root.classList.remove('light', 'dark');
  root.classList.add(theme);
  root.style.colorScheme = theme;
}

function readInitialTheme(): ThemeMode {
  if (typeof window === 'undefined') return 'dark';
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>('dark');

  useEffect(() => {
    const initial = readInitialTheme();
    setThemeState(initial);
    applyThemeClass(initial);
  }, []);

  const setTheme = useCallback((next: ThemeMode) => {
    setThemeState(next);
    applyThemeClass(next);
    window.localStorage.setItem(THEME_STORAGE_KEY, next);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const next: ThemeMode = prev === 'dark' ? 'light' : 'dark';
      applyThemeClass(next);
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme deve ser usado dentro de ThemeProvider');
  }
  return ctx;
}

/** Script inline no <head> — evita flash do tema errado. */
export const themeInitScript = `(function(){try{var k='${THEME_STORAGE_KEY}';var t=localStorage.getItem(k);var m=t==='light'||t==='dark'?t:(window.matchMedia('(prefers-color-scheme: light)').matches?'light':'dark');var r=document.documentElement;r.classList.remove('light','dark');r.classList.add(m);r.style.colorScheme=m;}catch(e){document.documentElement.classList.add('dark');}})();`;
