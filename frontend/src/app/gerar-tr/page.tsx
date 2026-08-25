'use client';

import { useState } from 'react';
import { Check, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { generateTR, extractErrorMessage } from '@/lib/api';
import PassoDados from '@/components/gerar-tr/PassoDados';
import PassoRequisitos from '@/components/gerar-tr/PassoRequisitos';
import ResultadoTR from '@/components/gerar-tr/ResultadoTR';
import { cn } from '@/lib/utils';

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
  const [resultado, setResultado] = useState<{
    filename_original: string;
    total_itens: number;
    document_id: string;
    itens: { item_number: string; title: string; content: string }[];
    html_completo?: string;
  } | null>(null);

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
      toast.success('HTML do Termo de Referência copiado', {
        description: 'Pronto para colar no SEI.',
      });
    }
  }

  return (
    <div className="animate-fade-in mx-auto max-w-4xl space-y-8">
      {/* Cabeçalho */}
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight text-content-primary">
          <Sparkles className="h-6 w-6 text-accent-400" aria-hidden />
          Assistente de Geração de TRs
        </h1>
        <p className="mt-1 text-sm text-content-muted">
          Gere um rascunho completo de Termo de Referência alinhado à Lei 14.133/2021, Lei
          13.303/2016 e jurisprudência do TCU.
        </p>
      </div>

      {error && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Indicador de Passos */}
      <ol className="grid grid-cols-3 gap-2">
        {STEPS.map((s) => {
          const active = step === s.num;
          const done = s.num === 3 && !!resultado;
          return (
            <li
              key={s.num}
              aria-current={active ? 'step' : undefined}
              className={cn(
                'rounded-xl border p-3 text-center transition-all',
                done
                  ? 'border-green-500/50 bg-green-500/15 text-green-300'
                  : active
                    ? 'border-accent-500/50 bg-accent-500/15 text-content-primary'
                    : 'border-line-subtle bg-panel/40 text-content-subtle',
              )}
            >
              <span className="tnum flex items-center justify-center gap-1 text-[11px] font-semibold uppercase tracking-wider">
                {done && <Check className="h-3 w-3" aria-hidden />}
                Passo {s.num}
              </span>
              <span className="mt-0.5 block text-xs">{s.label}</span>
            </li>
          );
        })}
      </ol>

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
