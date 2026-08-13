interface PassoDadosProps {
  tipoContratacao: string;
  objeto: string;
  justificativa: string;
  error: string | null;
  setTipoContratacao: (v: string) => void;
  setObjeto: (v: string) => void;
  setJustificativa: (v: string) => void;
  setError: (v: string | null) => void;
  onAvancar: () => void;
}

/**
 * Passo 1 do assistente: caracterização da necessidade (tipo, objeto, justificativa).
 */
export default function PassoDados({
  tipoContratacao,
  objeto,
  justificativa,
  error,
  setTipoContratacao,
  setObjeto,
  setJustificativa,
  setError,
  onAvancar,
}: PassoDadosProps) {
  function handleAvancar() {
    if (!objeto.trim() || !justificativa.trim()) {
      setError('Preencha o objeto e a justificativa para avançar.');
      return;
    }
    setError(null);
    onAvancar();
  }

  return (
    <div className="glass-card p-6 space-y-4">
      <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
        1. Caracterização da Necessidade
      </h2>

      <div className="space-y-4">
        <div>
          <label className="block text-xs text-gray-300 font-medium mb-1">
            Tipo de Contratação:
          </label>
          <select
            value={tipoContratacao}
            onChange={(e) => setTipoContratacao(e.target.value)}
            className="input-field w-full text-sm bg-surface-900"
          >
            <option value="servicos_continuados">Serviços Contínuos</option>
            <option value="obras_engenharia">Obras e Serviços de Engenharia</option>
            <option value="tecnologia_informacao">Tecnologia da Informação e Comunicação</option>
            <option value="compras_gerais">Aquisição de Bens / Compras Gerais</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-gray-300 font-medium mb-1">
            Descrição Clara do Objeto:
          </label>
          <textarea
            value={objeto}
            onChange={(e) => setObjeto(e.target.value)}
            rows={3}
            placeholder="Ex.: Contratação de empresa especializada na prestação de serviços continuados de manutenção preventiva e corretiva de ar condicionado central..."
            className="input-field w-full text-sm bg-surface-900"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-300 font-medium mb-1">
            Justificativa da Contratação:
          </label>
          <textarea
            value={justificativa}
            onChange={(e) => setJustificativa(e.target.value)}
            rows={4}
            placeholder="Ex.: A contratação faz-se necessária para manter a infraestrutura operacional da autoridade portuária em condições adequadas de uso, garantindo o conforto térmico..."
            className="input-field w-full text-sm bg-surface-900"
          />
        </div>
      </div>

      <div className="pt-2 flex justify-end">
        <button onClick={handleAvancar} className="btn-primary">
          Avançar para Passo 2 ➔
        </button>
      </div>
    </div>
  );
}
