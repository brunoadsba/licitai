'use client';

import { ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/Button';

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
    <div className="glass-card space-y-4 p-5 sm:p-6">
      <h2 className="text-[11px] font-medium uppercase tracking-widest text-content-subtle">
        1. Caracterização da Necessidade
      </h2>

      <div className="space-y-4">
        <div>
          <label htmlFor="tr-tipo" className="mb-1 block text-xs font-medium text-content-secondary">
            Tipo de Contratação
          </label>
          <select
            id="tr-tipo"
            value={tipoContratacao}
            onChange={(e) => setTipoContratacao(e.target.value)}
            className="input-field w-full text-sm"
          >
            <option value="servicos_continuados">Serviços Contínuos</option>
            <option value="obras_engenharia">Obras e Serviços de Engenharia</option>
            <option value="tecnologia_informacao">Tecnologia da Informação e Comunicação</option>
            <option value="compras_gerais">Aquisição de Bens / Compras Gerais</option>
          </select>
        </div>

        <div>
          <label htmlFor="tr-objeto" className="mb-1 block text-xs font-medium text-content-secondary">
            Descrição Clara do Objeto
          </label>
          <textarea
            id="tr-objeto"
            value={objeto}
            onChange={(e) => setObjeto(e.target.value)}
            rows={3}
            placeholder="Ex.: Contratação de empresa especializada na prestação de serviços continuados de manutenção preventiva e corretiva de ar condicionado central…"
            className="input-field w-full text-sm"
          />
        </div>

        <div>
          <label
            htmlFor="tr-justificativa"
            className="mb-1 block text-xs font-medium text-content-secondary"
          >
            Justificativa da Contratação
          </label>
          <textarea
            id="tr-justificativa"
            value={justificativa}
            onChange={(e) => setJustificativa(e.target.value)}
            rows={4}
            placeholder="Ex.: A contratação faz-se necessária para manter a infraestrutura operacional da autoridade portuária em condições adequadas de uso, garantindo o conforto térmico…"
            className="input-field w-full text-sm"
          />
        </div>
      </div>

      <div className="flex justify-end pt-2">
        <Button onClick={handleAvancar}>
          Avançar para Passo 2
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
