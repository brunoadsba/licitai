'use client';

import type { Art6ChecklistItem } from '@/types';
import { Badge } from '@/components/ui/Badge';

interface Art6ChecklistPanelProps {
  items: Art6ChecklistItem[];
}

/** Painel Art. 6º XXIII — alíneas faltantes/incertas no topo da análise. */
export default function Art6ChecklistPanel({ items }: Art6ChecklistPanelProps) {
  if (!items.length) return null;
  const gaps = items.filter((i) => i.status !== 'present');
  if (gaps.length === 0) {
    return (
      <div className="glass-card border-green-500/20 p-4">
        <p className="text-sm font-medium text-content-primary">Art. 6º, XXIII</p>
        <p className="mt-1 text-xs text-content-muted">
          Checklist a–j aparenta completo neste TR (heurística por palavras-chave).
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card border-amber-500/20 p-4">
      <p className="text-sm font-medium text-content-primary">
        Art. 6º, XXIII — {gaps.length} alínea(s) a revisar
      </p>
      <p className="mt-1 text-xs text-content-muted">
        Faltantes entram na fila Prioridade. Confirme no texto do TR antes de colar no SEI.
      </p>
      <ul className="mt-3 flex flex-wrap gap-2">
        {gaps.map((g) => (
          <li key={g.key}>
            <Badge tone={g.status === 'missing' ? 'critical' : 'medium'}>
              {g.alinea}) {g.label}
            </Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}
