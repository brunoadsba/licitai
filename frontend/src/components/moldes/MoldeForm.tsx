'use client';

import { Plus } from 'lucide-react';
import { MoldeConfig, RegraConfig } from '@/types';
import { Button } from '@/components/ui/Button';
import RegraEditor from './RegraEditor';

interface MoldeFormProps {
  editingId: string | null;
  nome: string;
  descricao: string;
  regras: RegraConfig[];
  saving: boolean;
  showJson: boolean;
  onNomeChange: (v: string) => void;
  onDescricaoChange: (v: string) => void;
  onAddRegra: () => void;
  onRegraChange: (index: number, campo: keyof RegraConfig, valor: unknown) => void;
  onRegraRemove: (index: number) => void;
  onSave: () => void;
  onToggleJson: () => void;
  montarConfig: () => MoldeConfig;
}

export default function MoldeForm({
  editingId,
  nome,
  descricao,
  regras,
  saving,
  showJson,
  onNomeChange,
  onDescricaoChange,
  onAddRegra,
  onRegraChange,
  onRegraRemove,
  onSave,
  onToggleJson,
  montarConfig,
}: MoldeFormProps) {
  return (
    <div className="glass-card p-5 sm:p-6">
      <h2 className="mb-4 text-lg font-semibold tracking-tight text-content-primary">
        {editingId ? 'Editar Molde' : 'Novo Molde'}
      </h2>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="molde-nome" className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
            Nome do molde
          </label>
          <input
            id="molde-nome"
            value={nome}
            onChange={(e) => onNomeChange(e.target.value)}
            placeholder="Ex.: Molde Padrão de TR"
            className="input-field w-full"
          />
        </div>
        <div>
          <label htmlFor="molde-descricao" className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
            Descrição
          </label>
          <input
            id="molde-descricao"
            value={descricao}
            onChange={(e) => onDescricaoChange(e.target.value)}
            placeholder="Descrição opcional"
            className="input-field w-full"
          />
        </div>
      </div>

      <div className="mb-3 flex items-center justify-between">
        <h3 className="tnum text-sm font-semibold text-content-secondary">Regras ({regras.length})</h3>
        <Button onClick={onAddRegra} variant="secondary" size="sm">
          <Plus className="h-3.5 w-3.5" aria-hidden />
          Adicionar Regra
        </Button>
      </div>

      {regras.length === 0 ? (
        <div className="glass-card p-8 text-center">
          <p className="text-sm text-content-muted">
            Nenhuma regra. Clique em &quot;Adicionar Regra&quot;.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {regras.map((regra, index) => (
            <RegraEditor
              key={index}
              regra={regra}
              index={index}
              onChange={onRegraChange}
              onRemove={onRegraRemove}
            />
          ))}
        </div>
      )}

      <div className="mt-6 flex items-center gap-3">
        <Button onClick={onSave} disabled={saving || regras.length === 0} loading={saving}>
          {saving ? 'Salvando…' : editingId ? 'Salvar Alterações' : 'Criar Molde'}
        </Button>
        <Button onClick={onToggleJson} variant="secondary">
          {showJson ? 'Ocultar JSON' : 'Ver JSON'}
        </Button>
      </div>

      {showJson && (
        <pre className="mt-4 overflow-x-auto whitespace-pre-wrap rounded-xl border border-line-strong bg-black/40 p-4 font-mono text-xs leading-relaxed text-green-400">
          {JSON.stringify(montarConfig(), null, 2)}
        </pre>
      )}
    </div>
  );
}
