import Link from 'next/link';
import { Badge, type Tone } from '@/components/ui/Badge';
import {
  CONFIDENCE_BLOCKS,
  CONFIDENCE_UPDATED,
  formatDateBR,
  isStale,
} from '@/lib/confidence';

export const metadata = {
  title: 'Como confiamos | LicitAI',
};

const STATUS_TONE: Record<string, Tone> = {
  medido: 'low',
  harness: 'medium',
  ausente: 'high',
  texto: 'neutral',
};

const STATUS_LABEL: Record<string, string> = {
  medido: 'medido',
  harness: 'em validação',
  ausente: 'ainda não medido',
  texto: 'doutrina',
};

export default function ConfiancaPage() {
  const stale = isStale(CONFIDENCE_UPDATED);
  return (
    <article className="animate-fade-in mx-auto max-w-2xl space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-content-primary">
          Como confiamos
        </h1>
        <p className="mt-1 text-sm text-content-muted">
          Números atualizados em {formatDateBR(CONFIDENCE_UPDATED)}. Piloto assistido: nada
          vai ao SEI sem sua aprovação.
        </p>
      </header>

      {stale && (
        <div
          role="alert"
          className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-200"
        >
          Números desatualizados (última medição há mais de 30 dias). Trate
          com cautela redobrada até nova medição.
        </div>
      )}

      <div className="space-y-3">
        {CONFIDENCE_BLOCKS.map((b) => (
          <section
            key={b.label}
            className="rounded-lg border border-line-subtle bg-surface/40 p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-semibold text-content-primary">{b.label}</h2>
              <Badge tone={STATUS_TONE[b.status]}>{STATUS_LABEL[b.status]}</Badge>
            </div>
            <p className="mt-1.5 text-sm text-content-secondary">{b.value}</p>
            <p className="mt-1 text-xs text-content-subtle">
              Fonte: {b.sourceHref ? <Link href={b.sourceHref}>{b.source}</Link> : b.source} ·{' '}
              {formatDateBR(b.lastUpdated)}
            </p>
          </section>
        ))}
      </div>

      <p className="text-sm text-content-muted">
        Entenda o fluxo em <Link href="/guia" className="underline">Como usar</Link>.
      </p>
    </article>
  );
}
