interface PassoRequisitosProps {
  valorEstimado: string;
  prazoMeses: number;
  criterioJulgamento: string;
  garantiaExigida: boolean;
  vistoriaExigida: boolean;
  loading: boolean;
  setValorEstimado: (v: string) => void;
  setPrazoMeses: (v: number) => void;
  setCriterioJulgamento: (v: string) => void;
  setGarantiaExigida: (v: boolean) => void;
  setVistoriaExigida: (v: boolean) => void;
  onVoltar: () => void;
  onGerar: () => void;
}

/**
 * Passo 2 do assistente: requisitos técnicos e financeiros + geração com IA.
 */
export default function PassoRequisitos({
  valorEstimado,
  prazoMeses,
  criterioJulgamento,
  garantiaExigida,
  vistoriaExigida,
  loading,
  setValorEstimado,
  setPrazoMeses,
  setCriterioJulgamento,
  setGarantiaExigida,
  setVistoriaExigida,
  onVoltar,
  onGerar,
}: PassoRequisitosProps) {
  return (
    <div className="glass-card p-6 space-y-4">
      <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
        2. Requisitos Técnicos & Financeiros
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-300 font-medium mb-1">
            Valor Estimado Global (R$):
          </label>
          <input
            type="number"
            value={valorEstimado}
            onChange={(e) => setValorEstimado(e.target.value)}
            placeholder="Ex.: 450000.00 (Opcional)"
            className="input-field w-full text-sm bg-surface-900"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-300 font-medium mb-1">
            Prazo de Vigência (Meses):
          </label>
          <input
            type="number"
            value={prazoMeses}
            onChange={(e) => setPrazoMeses(parseInt(e.target.value) || 12)}
            className="input-field w-full text-sm bg-surface-900"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-300 font-medium mb-1">
            Critério de Julgamento:
          </label>
          <select
            value={criterioJulgamento}
            onChange={(e) => setCriterioJulgamento(e.target.value)}
            className="input-field w-full text-sm bg-surface-900"
          >
            <option value="menor_preco">Menor Preço</option>
            <option value="maior_desconto">Maior Desconto</option>
            <option value="tecnica_preco">Técnica e Preço</option>
          </select>
        </div>

        <div className="space-y-3 pt-4">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-300">
            <input
              type="checkbox"
              checked={garantiaExigida}
              onChange={(e) => setGarantiaExigida(e.target.checked)}
              className="rounded border-white/20 bg-surface-900 text-primary-500"
            />
            Exigir Garantia Contratual (5%)
          </label>

          <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-300">
            <input
              type="checkbox"
              checked={vistoriaExigida}
              onChange={(e) => setVistoriaExigida(e.target.checked)}
              className="rounded border-white/20 bg-surface-900 text-primary-500"
            />
            Exigir Vistoria Técnica Prévia
          </label>
        </div>
      </div>

      <div className="pt-4 flex items-center justify-between">
        <button onClick={onVoltar} className="btn-secondary">
          ⬅ Voltar ao Passo 1
        </button>

        <button onClick={onGerar} disabled={loading} className="btn-primary">
          {loading ? 'Gerando TR com IA...' : '🪄 Gerar Termo de Referência Completo'}
        </button>
      </div>
    </div>
  );
}
