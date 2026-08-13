'use client';

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
          <div key={i} className="skeleton h-20" />
        ))}
      </div>
    );
  }

  if (moldes.length === 0) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-gray-500 text-sm">
          Nenhum molde cadastrado. Crie o primeiro.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {moldes.map((m) => (
        <div
          key={m.id}
          className={`glass-card-interactive p-4 cursor-pointer transition-all ${
            editingId === m.id ? 'ring-1 ring-primary-500/50' : ''
          }`}
          onClick={() => onSelect(m.id)}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-gray-200 truncate">
                {m.nome}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
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
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDryRun(m);
                }}
                className="p-1 rounded text-gray-400 hover:text-amber-300 hover:bg-amber-500/10 transition-all"
                title="Testar/Validar contra TR (Dry-Run)"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121 7.5z" />
                </svg>
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDuplicate(m.id);
                }}
                className="p-1 rounded text-gray-400 hover:text-primary-300 hover:bg-primary-500/10 transition-all"
                title="Duplicar molde"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v9.25c0 .621-.504 1.125-1.125 1.125z" />
                </svg>
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(m.id);
                }}
                className="p-1 rounded text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all"
                title="Remover molde"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
