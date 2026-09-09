'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FileUp, GitCompareArrows, LayoutGrid, ScrollText, Sparkles, Layers, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useShell } from './ShellContext';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/Sheet';

type NavItem = { href: string; label: string; icon: typeof LayoutGrid };

const NAV_GROUPS: { label?: string; items: NavItem[] }[] = [
  {
    items: [
      { href: '/', label: 'Painel', icon: LayoutGrid },
      { href: '/upload', label: 'Enviar Documento', icon: FileUp },
      { href: '/gerar-tr', label: 'Gerar TR', icon: Sparkles },
    ],
  },
  {
    label: 'Auditoria',
    items: [
      { href: '/comparacao', label: 'Comparações', icon: GitCompareArrows },
      { href: '/comparacao/versoes', label: 'Versões de TR', icon: ScrollText },
      { href: '/moldes', label: 'Moldes', icon: Layers },
    ],
  },
];

const ALL_HREFS = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.href));

/** Active = longest matching prefix (evita Comparações + Versões juntos). */
export function isNavActive(pathname: string, href: string, allHrefs: string[] = ALL_HREFS): boolean {
  if (href === '/') return pathname === '/';
  if (!pathname.startsWith(href)) return false;
  const hasLongerMatch = allHrefs.some(
    (other) => other !== href && other.length > href.length && pathname.startsWith(other),
  );
  return !hasLongerMatch;
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="flex-1 space-y-4 overflow-y-auto p-4" aria-label="Navegação principal">
      {NAV_GROUPS.map((group) => (
        <div key={group.label ?? 'main'} className="space-y-1">
          {group.label && (
            <p className="px-3 pb-1 text-[10px] font-medium uppercase tracking-widest text-content-subtle">
              {group.label}
            </p>
          )}
          {group.items.map((item) => {
            const active = isNavActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
                className={cn('sidebar-link', active && 'active')}
                aria-current={active ? 'page' : undefined}
              >
                <item.icon className="h-5 w-5 shrink-0" strokeWidth={1.75} aria-hidden />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}

function Brand() {
  return (
    <Link href="/" className="group block" aria-label="CODEBA — Autoridade Portuária, ir para o Painel">
      <div className="flex items-center justify-center rounded-xl bg-white px-3 py-2.5 shadow-sm transition-shadow group-hover:shadow-md">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/logo-codeba.png"
          alt="CODEBA — Autoridade Portuária"
          width={140}
          height={32}
          className="h-8 w-auto object-contain"
        />
      </div>
      <p className="mt-2.5 text-center text-[10px] font-medium uppercase tracking-widest text-content-subtle">
        Análise de TR • SEI
      </p>
    </Link>
  );
}

function SidebarFooter() {
  return (
    <div className="border-t border-line-subtle p-4">
      <p className="text-[11px] text-content-subtle">MVP v0.1.0 • SEI</p>
    </div>
  );
}

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      <div className="border-b border-line-subtle p-6">
        <Brand />
      </div>
      <NavLinks onNavigate={onNavigate} />
      <SidebarFooter />
    </>
  );
}

export default function Sidebar() {
  const { sidebarOpen, closeSidebar } = useShell();

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-line-subtle bg-panel lg:flex">
        <SidebarBody />
      </aside>

      <Sheet
        open={sidebarOpen}
        onOpenChange={(open) => {
          if (!open) closeSidebar();
        }}
      >
        <SheetContent
          side="left"
          hideClose
          className="lg:hidden"
          aria-label="Menu de navegação"
        >
          <SheetTitle className="sr-only">Menu de navegação</SheetTitle>
          <div className="flex items-center justify-between border-b border-line-subtle p-4 pr-2">
            <Brand />
            <button
              type="button"
              onClick={closeSidebar}
              aria-label="Fechar menu"
              className="rounded-md p-2 text-content-muted outline-none transition-colors hover:bg-white/[0.06] hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
            >
              <X className="h-5 w-5" aria-hidden />
            </button>
          </div>
          <NavLinks onNavigate={closeSidebar} />
          <SidebarFooter />
        </SheetContent>
      </Sheet>
    </>
  );
}
