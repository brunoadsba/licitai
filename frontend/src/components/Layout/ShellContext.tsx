'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';

const STORAGE_KEY = 'licitai-sidebar-collapsed';

interface ShellContextValue {
  /** Drawer lateral aberto (apenas < lg) */
  sidebarOpen: boolean;
  openSidebar: () => void;
  closeSidebar: () => void;
  /** Sidebar fixa oculta (apenas lg+) */
  desktopNavHidden: boolean;
  toggleDesktopNav: () => void;
  showDesktopNav: () => void;
  hideDesktopNav: () => void;
}

const ShellContext = createContext<ShellContextValue | null>(null);

export function ShellProvider({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [desktopNavHidden, setDesktopNavHidden] = useState(false);

  useEffect(() => {
    try {
      setDesktopNavHidden(localStorage.getItem(STORAGE_KEY) === '1');
    } catch {
      /* ignore */
    }
  }, []);

  const persist = useCallback((hidden: boolean) => {
    setDesktopNavHidden(hidden);
    try {
      localStorage.setItem(STORAGE_KEY, hidden ? '1' : '0');
    } catch {
      /* ignore */
    }
  }, []);

  return (
    <ShellContext.Provider
      value={{
        sidebarOpen,
        openSidebar: () => setSidebarOpen(true),
        closeSidebar: () => setSidebarOpen(false),
        desktopNavHidden,
        toggleDesktopNav: () => persist(!desktopNavHidden),
        showDesktopNav: () => persist(false),
        hideDesktopNav: () => persist(true),
      }}
    >
      {children}
    </ShellContext.Provider>
  );
}

export function useShell(): ShellContextValue {
  const ctx = useContext(ShellContext);
  if (!ctx) throw new Error('useShell deve ser usado dentro de <ShellProvider>');
  return ctx;
}
