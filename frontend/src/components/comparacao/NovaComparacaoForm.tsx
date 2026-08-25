'use client';

import { FileText, Play } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

interface NovaComparacaoFormProps {
  trs: { id: string; filename_original: string }[];
  moldes: { id: string; nome: string }[];
  propostas: { id: string; filename_original: string; total_items: number }[];
  propostaIds: string[];
  submitting: boolean;
  onToggleProposta: (id: string) => void;
  onStart: () => void;
  setTrId: (id: string) => void;
  setMoldeId: (id: string) => void;
}

/**
 * Formulário de nova comparação: seleção de TR, molde e propostas.
 */
export default function NovaComparacaoForm({
  trs,
  moldes,
  propostas,
  propostaIds,
  submitting,
  onToggleProposta,
  onStart,
  setTrId,
  setMoldeId,
}: NovaComparacaoFormProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
          Termo de Referência
        </label>
        <select
          onChange={(e) => setTrId(e.target.value)}
          className="input-field w-full"
          aria-label="Termo de Referência"
        >
          <option value="">Selecione o TR…</option>
          {trs.map((tr) => (
            <option key={tr.id} value={tr.id}>
              {tr.filename_original}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
          Molde de Regras
        </label>
        <select
          onChange={(e) => setMoldeId(e.target.value)}
          className="input-field w-full"
          aria-label="Molde de Regras"
        >
          <option value="">Selecione o molde…</option>
          {moldes.map((m) => (
            <option key={m.id} value={m.id}>
              {m.nome}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
          <span className="tnum">Propostas ({propostaIds.length} selecionada(s))</span>
        </label>
        <div className="max-h-48 space-y-2 overflow-y-auto pr-1">
          {propostas.length === 0 ? (
            <p className="text-sm text-content-muted">
              Nenhuma proposta cadastrada. Envie uma abaixo.
            </p>
          ) : (
            propostas.map((p) => {
              const selected = propostaIds.includes(p.id);
              return (
                <button
                  key={p.id}
                  onClick={() => onToggleProposta(p.id)}
                  aria-pressed={selected}
                  className={cn(
                    'w-full rounded-xl border p-3 text-left outline-none transition-all duration-150',
                    'focus-visible:ring-2 focus-visible:ring-accent-500/60',
                    selected
                      ? 'border-accent-500/40 bg-accent-500/10'
                      : 'glass-card-interactive border-transparent',
                  )}
                >
                  <p className="truncate text-sm font-medium text-content-primary">
                    {p.filename_original}
                  </p>
                  <p className="tnum mt-0.5 text-xs text-content-subtle">{p.total_items} itens</p>
                </button>
              );
            })
          )}
        </div>
      </div>

      <Button onClick={onStart} loading={submitting} disabled={submitting} className="w-full">
        {!submitting && <Play className="h-4 w-4" aria-hidden />}
        {submitting ? 'Iniciando…' : 'Iniciar Comparação'}
      </Button>
    </div>
  );
}
