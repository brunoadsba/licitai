import Link from 'next/link';
import { ArrowRightLeft, FilePenLine, GitCompareArrows, Layers, Scale } from 'lucide-react';
import { copy } from '@/lib/copy';

export const metadata = {
  title: 'Complementos | LicitAI',
};

const TOOLS = [
  {
    href: '/gerar-tr',
    title: 'Gerar TR',
    blurb: 'Monta um rascunho de Termo de Referência a partir dos dados que você informar.',
    icon: FilePenLine,
  },
  {
    href: '/comparacao',
    title: 'Comparações',
    blurb: 'Compara o TR com propostas de fornecedor.',
    icon: GitCompareArrows,
  },
  {
    href: '/comparacao/versoes',
    title: 'Versões de TR',
    blurb: 'Mostra o que mudou entre duas versões do mesmo TR.',
    icon: ArrowRightLeft,
  },
  {
    href: '/moldes',
    title: 'Moldes',
    blurb: 'Regras extras para checar o TR além da análise usual.',
    icon: Layers,
  },
  {
    href: '/legal',
    title: copy.nav.consultarLei,
    blurb: 'Lê o texto da lei e do artigo. Também abre pelo link da citação.',
    icon: Scale,
  },
] as const;

export default function ComplementosPage() {
  return (
    <div className="animate-fade-in mx-auto max-w-4xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-content-primary">
          {copy.nav.complementos}
        </h1>
        <p className="mt-1 text-sm text-content-muted">
          Apoiam o TR além de enviar, revisar e copiar para o SEI. Use só se precisar.
        </p>
      </header>

      <ul className="grid gap-3 sm:grid-cols-2">
        {TOOLS.map((tool) => (
          <li key={tool.href}>
            <Link
              href={tool.href}
              className="glass-card-interactive flex h-full gap-3 px-5 py-4 outline-none focus-visible:ring-2 focus-visible:ring-accent-500/60"
            >
              <tool.icon
                className="mt-0.5 h-5 w-5 shrink-0 text-accent-500"
                strokeWidth={1.75}
                aria-hidden
              />
              <span>
                <span className="block text-sm font-medium text-content-primary">{tool.title}</span>
                <span className="mt-1 block text-sm text-content-muted">{tool.blurb}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
