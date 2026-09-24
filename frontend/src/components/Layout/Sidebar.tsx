'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FileUp, Layers, LayoutGrid, PanelLeftClose, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useShell } from './ShellContext';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/Sheet';
import { copy } from '@/lib/copy';

type NavItem = { href: string; label: string; icon: typeof LayoutGrid };

const PRIMARY_NAV: NavItem[] = [
  { href: '/', label: copy.nav.painel, icon: LayoutGrid },
  { href: '/upload', label: copy.nav.enviarTr, icon: FileUp },
  { href: '/complementos', label: copy.nav.complementos, icon: Layers },
];

const ALL_HREFS = PRIMARY_NAV.map((i) => i.href);

const COMPLEMENTO_PREFIXES = ['/gerar-tr', '/comparacao', '/moldes', '/legal'] as const;

/** Active = longest matching prefix. */
export function isNavActive(pathname: string, href: string, allHrefs: string[] = ALL_HREFS): boolean {
  if (href === '/complementos') {
    return (
      pathname === '/complementos' ||
      COMPLEMENTO_PREFIXES.some((prefix) => pathname.startsWith(prefix))
    );
  }
  if (href === '/') return pathname === '/';
  if (!pathname.startsWith(href)) return false;
  const hasLongerMatch = allHrefs.some(
    (other) => other !== href && other.length > href.length && pathname.startsWith(other),
  );
  return !hasLongerMatch;
}

function NavItemLink({
  item,
  onNavigate,
}: {
  item: NavItem;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const active = isNavActive(pathname, item.href);
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      className={cn('sidebar-link', active && 'active')}
      aria-current={active ? 'page' : undefined}
    >
      <item.icon className="h-5 w-5 shrink-0" strokeWidth={1.75} aria-hidden />
      <span>{item.label}</span>
    </Link>
  );
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex-1 space-y-1 overflow-y-auto p-4" aria-label="Navegação principal">
      {PRIMARY_NAV.map((item) => (
        <NavItemLink key={item.href} item={item} onNavigate={onNavigate} />
      ))}
    </nav>
  );
}

function Brand() {
  return (
    <Link href="/" className="group block" aria-label="CODEBA — Autoridade Portuária, ir para o Painel">
      <div className="flex items-center justify-center rounded-xl border border-white/10 bg-white px-3 py-2.5 shadow-soft transition-all group-hover:border-accent-400/30 group-hover:shadow-accent">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/logo-codeba.png"
          alt="CODEBA — Autoridade Portuária"
          width={140}
          height={32}
          className="h-8 w-auto object-contain"
        />
      </div>
    </Link>
  );
}

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  const { hideDesktopNav } = useShell();

  return (
    <>
      <div className="relative border-b border-line-subtle p-6">
        <button
          type="button"
          onClick={hideDesktopNav}
          aria-label="Esconder menu lateral"
          title="Esconder menu"
          className="absolute right-3 top-3 hidden rounded-md p-1.5 text-content-subtle outline-none transition-colors hover:bg-white/[0.06] hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60 lg:inline-flex"
        >
          <PanelLeftClose className="h-4 w-4" aria-hidden />
        </button>
        <Brand />
      </div>
      <NavLinks onNavigate={onNavigate} />
    </>
  );
}

export default function Sidebar() {
  const { sidebarOpen, closeSidebar, desktopNavHidden } = useShell();

  return (
    <>
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-line-subtle bg-panel/95 backdrop-blur-xl transition-transform duration-200 ease-out lg:flex',
          desktopNavHidden && '-translate-x-full pointer-events-none',
        )}
        aria-hidden={desktopNavHidden}
      >
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
        </SheetContent>
      </Sheet>
    </>
  );
}
