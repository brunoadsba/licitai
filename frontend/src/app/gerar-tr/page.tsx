'use client';

import { useState } from 'react';
import { generateTR , extractErrorMessage } from '@/lib/api';
import PassoDados from '@/components/gerar-tr/PassoDados';
import PassoRequisitos from '@/components/gerar-tr/PassoRequisitos';
import ResultadoTR from '@/components/gerar-tr/ResultadoTR';

const STEPS = [
  { num: 1, label: 'Dados da Contratação' },
  { num: 2, label: 'Requisitos & Prazos' },
  { num: 3, label: 'Resultado & SEI' },
];

export default function GerarTRPage() {
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
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao gerar Termo de Referência.'));
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
        {STEPS.map((s) => {
          const active = step === s.num;
          const done = s.num === 3 && !!resultado;
          return (
            <div
              key={s.num}
              className={`p-3 rounded-xl border text-center transition-all ${
                active || done
                  ? done
                    ? 'bg-green-500/20 border-green-500/50 text-green-300'
                    : 'bg-primary-500/20 border-primary-500/50 text-white'
                  : 'bg-surface-900/40 border-white/5 text-gray-500'
              }`}
            >
              <span className="text-xs font-bold block">PASSO {s.num}</span>
              <span className="text-xs">{s.label}</span>
            </div>
          );
        })}
      </div>

      {/* PASSO 1 */}
      {step === 1 && (
        <PassoDados
          tipoContratacao={tipoContratacao}
          objeto={objeto}
          justificativa={justificativa}
          error={error}
          setTipoContratacao={setTipoContratacao}
          setObjeto={setObjeto}
          setJustificativa={setJustificativa}
          setError={setError}
          onAvancar={() => setStep(2)}
        />
      )}

      {/* PASSO 2 */}
      {step === 2 && (
        <PassoRequisitos
          valorEstimado={valorEstimado}
          prazoMeses={prazoMeses}
          criterioJulgamento={criterioJulgamento}
          garantiaExigida={garantiaExigida}
          vistoriaExigida={vistoriaExigida}
          loading={loading}
          setValorEstimado={setValorEstimado}
          setPrazoMeses={setPrazoMeses}
          setCriterioJulgamento={setCriterioJulgamento}
          setGarantiaExigida={setGarantiaExigida}
          setVistoriaExigida={setVistoriaExigida}
          onVoltar={() => setStep(1)}
          onGerar={handleGenerate}
        />
      )}

      {/* PASSO 3 - RESULTADO */}
      {step === 3 && resultado && (
        <ResultadoTR
          resultado={resultado}
          onCopiarHtml={copyHtml}
          onRecomecar={() => setStep(1)}
        />
      )}
    </div>
  );
}
