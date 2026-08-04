'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { generateTR } from '@/lib/api';

export default function GerarTRPage() {
  const router = useRouter();

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Parâmetros do formulário
  const [tipoContratacao, setTipoContratacao] = useState('servicos_continuados');
  const [objeto, setObjeto] = useState('');
  const [justificativa, setJustificativa] = useState('');
  const [valorEstimado, setValorEstimado] = useState<string>('');
  const [prazoMeses, setPrazoMeses] = useState<number>(12);
  const [garantiaExigida, setGarantiaExigida] = useState(false);
  const [vistoriaExigida, setVistoriaExigida] = useState(false);
  const [criterioJulgamento, setCriterioJulgamento] = useState('menor_preco');

  // Resultado
  const [resultado, setResultado] = useState<any | null>(null);

  async function handleGenerate() {
    if (!objeto.trim() || objeto.length < 10) {
      setError('Descreva o objeto da contratação com pelo menos 10 caracteres.');
      return;
    }
    if (!justificativa.trim() || justificativa.length < 15) {
      setError('Informe a justificativa da contratação com pelo menos 15 caracteres.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await generateTR({
        tipo_contratacao: tipoContratacao,
        objeto: objeto.trim(),
        justificativa: justificativa.trim(),
        valor_estimado: valorEstimado ? parseFloat(valorEstimado) : undefined,
        prazo_meses: prazoMeses,
        garantia_exigida: garantiaExigida,
        vistoria_exigida: vistoriaExigida,
        criterio_julgamento: criterioJulgamento,
      });

      setResultado(res);
      setStep(3);
    } catch (err: any) {
      setError(err.message || 'Erro ao gerar Termo de Referência.');
    } finally {
      setLoading(false);
    }
  }

  function copyHtml() {
    if (resultado?.html_completo) {
      navigator.clipboard.writeText(resultado.html_completo);
      alert('HTML do Termo de Referência copiado para a área de transferência! Pronto para colar no SEI.');
    }
  }

  return (
    <div className="space-y-8 animate-fade-in max-w-4xl mx-auto">
      {/* Cabeçalho */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <span>🪄</span> Assistente de Geração de TRs
        </h1>
        <p className="text-gray-400 mt-1 text-sm">
          Gere um rascunho completo de Termo de Referência alinhado à Lei 14.133/2021, Lei 13.303/2016 e jurisprudência do TCU.
        </p>
      </div>

      {error && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Indicador de Passos */}
      <div className="grid grid-cols-3 gap-2">
        <div className={`p-3 rounded-xl border text-center transition-all ${step === 1 ? 'bg-primary-500/20 border-primary-500/50 text-white' : 'bg-surface-900/40 border-white/5 text-gray-500'}`}>
          <span className="text-xs font-bold block">PASSO 1</span>
          <span className="text-xs">Dados da Contratação</span>
        </div>
        <div className={`p-3 rounded-xl border text-center transition-all ${step === 2 ? 'bg-primary-500/20 border-primary-500/50 text-white' : 'bg-surface-900/40 border-white/5 text-gray-500'}`}>
          <span className="text-xs font-bold block">PASSO 2</span>
          <span className="text-xs">Requisitos & Prazos</span>
        </div>
        <div className={`p-3 rounded-xl border text-center transition-all ${step === 3 ? 'bg-green-500/20 border-green-500/50 text-green-300' : 'bg-surface-900/40 border-white/5 text-gray-500'}`}>
          <span className="text-xs font-bold block">PASSO 3</span>
          <span className="text-xs">Resultado & SEI</span>
        </div>
      </div>

      {/* PASSO 1 */}
      {step === 1 && (
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
            <button
              onClick={() => {
                if (!objeto.trim() || !justificativa.trim()) {
                  setError('Preencha o objeto e a justificativa para avançar.');
                  return;
                }
                setError(null);
                setStep(2);
              }}
              className="btn-primary"
            >
              Avançar para Passo 2 ➔
            </button>
          </div>
        </div>
      )}

      {/* PASSO 2 */}
      {step === 2 && (
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
            <button
              onClick={() => setStep(1)}
              className="btn-secondary"
            >
              ⬅ Voltar ao Passo 1
            </button>

            <button
              onClick={handleGenerate}
              disabled={loading}
              className="btn-primary"
            >
              {loading ? 'Gerando TR com IA...' : '🪄 Gerar Termo de Referência Completo'}
            </button>
          </div>
        </div>
      )}

      {/* PASSO 3 - RESULTADO */}
      {step === 3 && resultado && (
        <div className="space-y-6">
          <div className="glass-card p-6 border-green-500/30 space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div>
                <span className="badge badge-success text-[10px] uppercase">Geração Concluída</span>
                <h2 className="text-xl font-bold text-white mt-1">{resultado.filename_original}</h2>
                <p className="text-xs text-gray-400">Total de {resultado.total_itens} seções geradas com fundamentação no TCU</p>
              </div>

              <div className="flex items-center gap-2">
                <button onClick={copyHtml} className="btn-primary text-xs">
                  📋 Copiar HTML para SEI
                </button>
                <button
                  onClick={() => router.push(`/analysis/${resultado.document_id}`)}
                  className="btn-secondary text-xs"
                >
                  🔍 Auditar no LicitAI
                </button>
              </div>
            </div>

            {/* Exibição das seções geradas */}
            <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
              {resultado.itens.map((item: any) => (
                <div key={item.item_number} className="p-4 bg-surface-900/60 rounded-xl border border-white/10 space-y-2">
                  <span className="font-mono text-xs font-bold text-primary-400">{item.item_number} {item.title}</span>
                  <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">{item.content}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-start">
            <button onClick={() => setStep(1)} className="btn-secondary">
              🔄 Criar Outro Termo de Referência
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
