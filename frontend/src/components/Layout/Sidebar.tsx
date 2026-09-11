'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ChevronDown,
  FileUp,
  GitCompareArrows,
  LayoutGrid,
  ScrollText,
  FilePenLine,
  Layers,
  BookOpen,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useShell } from './ShellContext';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/Sheet';

type NavItem = { href: string; label: string; icon: typeof LayoutGrid };

/** Fluxo principal do elaborador — uma ação de envio, sem competir com Gerar TR. */
const PRIMARY_NAV: NavItem[] = [
  { href: '/', label: 'Painel', icon: LayoutGrid },
  { href: '/upload', label: 'Enviar TR', icon: FileUp },
];

const EXTRA_NAV: NavItem[] = [
  { href: '/gerar-tr', label: 'Gerar TR', icon: FilePenLine },
  { href: '/comparacao', label: 'Comparações', icon: GitCompareArrows },
  { href: '/comparacao/versoes', label: 'Versões de TR', icon: ScrollText },
  { href: '/moldes', label: 'Moldes', icon: Layers },
  { href: '/guia', label: 'Guia do usuário', icon: BookOpen },
];

const ALL_HREFS = [...PRIMARY_NAV, ...EXTRA_NAV].map((i) => i.href);

/** Active = longest matching prefix (evita Comparações + Versões juntos). */
export function isNavActive(pathname: string, href: string, allHrefs: string[] = ALL_HREFS): boolean {
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
  const pathname = usePathname();
  const extrasActive = EXTRA_NAV.some((item) => isNavActive(pathname, item.href));
  const [extrasOpen, setExtrasOpen] = useState(extrasActive);

  return (
    <nav className="flex-1 space-y-4 overflow-y-auto p-4" aria-label="Navegação principal">
      <div className="space-y-1">
        <p className="px-3 pb-1 text-[10px] font-medium uppercase tracking-widest text-content-subtle">
          Revisar TR
        </p>
        {PRIMARY_NAV.map((item) => (
          <NavItemLink key={item.href} item={item} onNavigate={onNavigate} />
        ))}
      </div>

      <div className="space-y-1">
        <button
          type="button"
          onClick={() => setExtrasOpen((v) => !v)}
          className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-[10px] font-medium uppercase tracking-widest text-content-subtle outline-none hover:bg-white/[0.04] focus-visible:ring-2 focus-visible:ring-accent-500/60"
          aria-expanded={extrasOpen}
        >
          Mais ferramentas
          <ChevronDown
            className={cn('h-3.5 w-3.5 transition-transform', extrasOpen && 'rotate-180')}
            aria-hidden
          />
        </button>
        {extrasOpen && (
          <div className="space-y-1">
            {EXTRA_NAV.map((item) => (
              <NavItemLink key={item.href} item={item} onNavigate={onNavigate} />
            ))}
          </div>
        )}
      </div>
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
      <p className="mt-2.5 text-center text-[10px] font-medium uppercase tracking-[0.14em] text-content-subtle">
        Revisar TR · SEI
      </p>
    </Link>
  );
}

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      <div className="border-b border-line-subtle p-6">
        <Brand />
      </div>
      <NavLinks onNavigate={onNavigate} />
    </>
  );
}

export default function Sidebar() {
  const { sidebarOpen, closeSidebar } = useShell();

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-line-subtle bg-panel/95 backdrop-blur-xl lg:flex">
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
