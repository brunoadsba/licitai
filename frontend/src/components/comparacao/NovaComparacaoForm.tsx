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
        <label className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
          Termo de Referência
        </label>
        <select
          onChange={(e) => setTrId(e.target.value)}
          className="input-field w-full"
        >
          <option value="">Selecione o TR...</option>
          {trs.map((tr) => (
            <option key={tr.id} value={tr.id}>
              {tr.filename_original}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
          Molde de Regras
        </label>
        <select
          onChange={(e) => setMoldeId(e.target.value)}
          className="input-field w-full"
        >
          <option value="">Selecione o molde...</option>
          {moldes.map((m) => (
            <option key={m.id} value={m.id}>
              {m.nome}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
          Propostas ({propostaIds.length} selecionada(s))
        </label>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {propostas.length === 0 ? (
            <p className="text-sm text-gray-500">
              Nenhuma proposta cadastrada. Envie uma abaixo.
            </p>
          ) : (
            propostas.map((p) => (
              <button
                key={p.id}
                onClick={() => onToggleProposta(p.id)}
                className={`w-full text-left p-3 rounded-xl border transition-all ${
                  propostaIds.includes(p.id)
                    ? 'bg-primary-500/10 border-primary-500/40'
                    : 'glass-card-interactive'
                }`}
              >
                <p className="text-sm text-gray-200 font-medium truncate">
                  {p.filename_original}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {p.total_items} itens
                </p>
              </button>
            ))
          )}
        </div>
      </div>

      <button
        onClick={onStart}
        disabled={submitting}
        className="btn-primary w-full"
      >
        {submitting ? 'Iniciando...' : 'Iniciar Comparação'}
      </button>
    </div>
  );
}
