'use client';

import { MoldeConfig, RegraConfig } from '@/types';
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
    <div className="glass-card p-6">
      <h2 className="text-lg font-semibold text-white mb-4">
        {editingId ? 'Editar Molde' : 'Novo Molde'}
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
            Nome do molde
          </label>
          <input
            value={nome}
            onChange={(e) => onNomeChange(e.target.value)}
            placeholder="Ex.: Molde Padrão de TR"
            className="input-field w-full"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
            Descrição
          </label>
          <input
            value={descricao}
            onChange={(e) => onDescricaoChange(e.target.value)}
            placeholder="Descrição opcional"
            className="input-field w-full"
          />
        </div>
      </div>

      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-300">
          Regras ({regras.length})
        </h3>
        <button
          onClick={onAddRegra}
          className="btn-secondary text-xs"
        >
          + Adicionar Regra
        </button>
      </div>

      {regras.length === 0 ? (
        <div className="glass-card p-8 text-center">
          <p className="text-gray-500 text-sm">
            Nenhuma regra. Clique em &quot;+ Adicionar Regra&quot;.
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

      <div className="flex items-center gap-3 mt-6">
        <button
          onClick={onSave}
          disabled={saving || regras.length === 0}
          className="btn-primary"
        >
          {saving ? 'Salvando...' : editingId ? 'Salvar Alterações' : 'Criar Molde'}
        </button>
        <button
          onClick={onToggleJson}
          className="btn-secondary"
        >
          {showJson ? 'Ocultar JSON' : 'Ver JSON'}
        </button>
      </div>

      {showJson && (
        <pre className="mt-4 p-4 bg-black/40 border border-white/10 rounded-xl text-xs text-green-400 overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(montarConfig(), null, 2)}
        </pre>
      )}
    </div>
  );
}
