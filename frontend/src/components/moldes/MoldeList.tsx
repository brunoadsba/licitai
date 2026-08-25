'use client';

import { Copy, FlaskConical, Layers, Trash2 } from 'lucide-react';
import { Skeleton } from '@/components/ui/Skeleton';
import { Molde, MoldeConfig } from '@/types';

interface MoldeListProps {
  moldes: Molde[];
  loading: boolean;
  editingId: string | null;
  onSelect: (id: string) => void;
  onDryRun: (molde: Molde) => void;
  onDuplicate: (id: string) => void;
  onRemove: (id: string) => void;
}

export default function MoldeList({
  moldes,
  loading,
  editingId,
  onSelect,
  onDryRun,
  onDuplicate,
  onRemove,
}: MoldeListProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    );
  }

  if (moldes.length === 0) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-sm text-content-muted">Nenhum molde cadastrado. Crie o primeiro.</p>
      </div>
    );
  }

  const iconButton =
    'rounded-md p-1.5 text-content-subtle outline-none transition-colors focus-visible:ring-2 focus-visible:ring-accent-500/60';

  return (
    <div className="space-y-2">
      {moldes.map((m) => (
        <div
          key={m.id}
          role="button"
          tabIndex={0}
          onClick={() => onSelect(m.id)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onSelect(m.id);
            }
          }}
          className={`glass-card-interactive cursor-pointer p-4 outline-none focus-visible:ring-2 focus-visible:ring-accent-500/60 ${
            editingId === m.id ? 'ring-1 ring-accent-500/50' : ''
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-content-primary">{m.nome}</p>
              <p className="tnum mt-0.5 flex items-center gap-1 text-xs text-content-subtle">
                <Layers className="h-3 w-3" aria-hidden />
                {(() => {
                  try {
                    const c = JSON.parse(m.config_json) as MoldeConfig;
                    return `${c.regras.length} regras`;
                  } catch {
                    return 'config inválido';
                  }
                })()}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-0.5">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDryRun(m);
                }}
                aria-label={`Testar ${m.nome} contra TR (dry-run)`}
                title="Testar/Validar contra TR (Dry-Run)"
                className={`${iconButton} hover:bg-amber-500/10 hover:text-amber-300`}
              >
                <FlaskConical className="h-4 w-4" aria-hidden />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDuplicate(m.id);
                }}
                aria-label={`Duplicar ${m.nome}`}
                title="Duplicar molde"
                className={`${iconButton} hover:bg-accent-500/10 hover:text-accent-400`}
              >
                <Copy className="h-4 w-4" aria-hidden />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(m.id);
                }}
                aria-label={`Remover ${m.nome}`}
                title="Remover molde"
                className={`${iconButton} hover:bg-red-500/10 hover:text-red-400`}
              >
                <Trash2 className="h-4 w-4" aria-hidden />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
