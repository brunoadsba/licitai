'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { FileUp, GitCompareArrows, LayoutGrid, ScrollText, Sparkles, Layers, X } from 'lucide-react';
import { AnimatePresence, motion, MotionConfig } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useShell } from './ShellContext';

const NAV_ITEMS = [
  { href: '/', label: 'Painel', icon: LayoutGrid },
  { href: '/upload', label: 'Enviar Documento', icon: FileUp },
  { href: '/gerar-tr', label: 'Gerar TR', icon: Sparkles },
  { href: '/comparacao', label: 'Comparações', icon: GitCompareArrows },
  { href: '/comparacao/versoes', label: 'Versões de TR', icon: ScrollText },
  { href: '/moldes', label: 'Moldes', icon: Layers },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="flex-1 space-y-1 p-4" aria-label="Navegação principal">
      {NAV_ITEMS.map((item) => {
        const isActive =
          item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn('sidebar-link', isActive && 'active')}
            aria-current={isActive ? 'page' : undefined}
          >
            <item.icon className="h-5 w-5 shrink-0" strokeWidth={1.75} aria-hidden />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function Brand() {
  return (
    <Link href="/" className="group flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-600 shadow-rim transition-colors group-hover:bg-accent-500">
        <ScrollText className="h-5 w-5 text-white" strokeWidth={1.75} aria-hidden />
      </div>
      <div>
        <h1 className="text-sm font-semibold tracking-tight text-content-primary">Análise de TR</h1>
        <p className="text-[10px] uppercase tracking-widest text-content-subtle">Sistema SEI</p>
      </div>
    </Link>
  );
}

function SidebarFooter() {
  return (
    <div className="border-t border-line-subtle p-4">
      <p className="text-[11px] text-content-subtle">MVP v0.1.0</p>
    </div>
  );
}

export default function Sidebar() {
  const { sidebarOpen, closeSidebar } = useShell();
  const pathname = usePathname();

  useEffect(() => {
    if (!sidebarOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeSidebar();
    };
    window.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [sidebarOpen, closeSidebar]);

  return (
    <>
      {/* Desktop: fixa à esquerda */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-line-subtle bg-panel lg:flex">
        <div className="border-b border-line-subtle p-6">
          <Brand />
        </div>
        <NavLinks />
        <SidebarFooter />
      </aside>

      {/* Mobile: drawer com overlay */}
      <MotionConfig reducedMotion="user">
        <AnimatePresence>
          {sidebarOpen && (
            <div
              className="fixed inset-0 z-50 lg:hidden"
              role="dialog"
              aria-modal="true"
              aria-label="Menu de navegação"
            >
              <motion.button
                aria-label="Fechar menu"
                className="absolute inset-0 bg-black/70 backdrop-blur-[2px]"
                onClick={closeSidebar}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              />
              <motion.aside
                className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col border-r border-line-subtle bg-panel shadow-drawer"
                initial={{ x: '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: '-100%' }}
                transition={{ type: 'spring', stiffness: 400, damping: 40 }}
              >
                <div className="flex items-center justify-between border-b border-line-subtle p-4 pr-2">
                  <Brand />
                  <button
                    onClick={closeSidebar}
                    aria-label="Fechar menu"
                    className="rounded-md p-2 text-content-muted outline-none transition-colors hover:bg-white/[0.06] hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
                  >
                    <X className="h-5 w-5" aria-hidden />
                  </button>
                </div>
                <NavLinks onNavigate={closeSidebar} />
                <SidebarFooter />
              </motion.aside>
            </div>
          )}
        </AnimatePresence>
      </MotionConfig>
    </>
  );
}
