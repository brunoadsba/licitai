'use client';

import { ArrowLeft, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/Button';

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
    <div className="glass-card space-y-4 p-5 sm:p-6">
      <h2 className="text-[11px] font-medium uppercase tracking-widest text-content-subtle">
        2. Requisitos Técnicos &amp; Financeiros
      </h2>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="tr-valor" className="mb-1 block text-xs font-medium text-content-secondary">
            Valor Estimado Global (R$)
          </label>
          <input
            id="tr-valor"
            type="number"
            value={valorEstimado}
            onChange={(e) => setValorEstimado(e.target.value)}
            placeholder="Ex.: 450000.00 (Opcional)"
            className="input-field tnum w-full text-sm"
          />
        </div>

        <div>
          <label htmlFor="tr-prazo" className="mb-1 block text-xs font-medium text-content-secondary">
            Prazo de Vigência (Meses)
          </label>
          <input
            id="tr-prazo"
            type="number"
            value={prazoMeses}
            onChange={(e) => setPrazoMeses(parseInt(e.target.value) || 12)}
            className="input-field tnum w-full text-sm"
          />
        </div>

        <div>
          <label htmlFor="tr-criterio" className="mb-1 block text-xs font-medium text-content-secondary">
            Critério de Julgamento
          </label>
          <select
            id="tr-criterio"
            value={criterioJulgamento}
            onChange={(e) => setCriterioJulgamento(e.target.value)}
            className="input-field w-full text-sm"
          >
            <option value="menor_preco">Menor Preço</option>
            <option value="maior_desconto">Maior Desconto</option>
            <option value="tecnica_preco">Técnica e Preço</option>
          </select>
        </div>

        <div className="space-y-3 pt-1 sm:pt-6">
          <label className="flex cursor-pointer items-center gap-2 text-xs text-content-secondary">
            <input
              type="checkbox"
              checked={garantiaExigida}
              onChange={(e) => setGarantiaExigida(e.target.checked)}
              className="h-4 w-4 rounded border-line-strong bg-canvas accent-accent-500"
            />
            Exigir Garantia Contratual (5%)
          </label>

          <label className="flex cursor-pointer items-center gap-2 text-xs text-content-secondary">
            <input
              type="checkbox"
              checked={vistoriaExigida}
              onChange={(e) => setVistoriaExigida(e.target.checked)}
              className="h-4 w-4 rounded border-line-strong bg-canvas accent-accent-500"
            />
            Exigir Vistoria Técnica Prévia
          </label>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 pt-4">
        <Button onClick={onVoltar} variant="secondary">
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Voltar ao Passo 1
        </Button>

        <Button onClick={onGerar} disabled={loading} loading={loading}>
          {!loading && <Sparkles className="h-4 w-4" aria-hidden />}
          {loading ? 'Gerando TR com IA…' : 'Gerar Termo de Referência Completo'}
        </Button>
      </div>
    </div>
  );
}
