'use client';

import { X } from 'lucide-react';
import { AnchorTipo, ANCHOR_TIPO_LABELS, RegraConfig } from '@/types';

const TIPOS: AnchorTipo[] = [
  'numero_inteiro',
  'numero_extenso',
  'booleano',
  'legal',
  'data',
  'percentual',
  'monetario',
  'cnpj',
  'prazo_relativo',
  'cep',
];

interface RegraEditorProps {
  regra: RegraConfig;
  index: number;
  onChange: (index: number, campo: keyof RegraConfig, valor: unknown) => void;
  onRemove: (index: number) => void;
}

export default function RegraEditor({ regra, index, onChange, onRemove }: RegraEditorProps) {
  function handlePalavras(raw: string) {
    const palavras = raw
      .split(',')
      .map((p) => p.trim())
      .filter(Boolean);
    onChange(index, 'palavras_chave', palavras);
  }

  return (
    <div className="glass-card space-y-4 p-4">
      <div className="flex items-center justify-between">
        <span className="tnum text-[11px] uppercase tracking-widest text-content-subtle">
          Regra {index + 1}
        </span>
        <button
          onClick={() => onRemove(index)}
          aria-label={`Remover regra ${index + 1}`}
          className="rounded-md p-1 text-content-subtle outline-none transition-colors hover:bg-red-500/10 hover:text-red-400 focus-visible:ring-2 focus-visible:ring-red-500/60"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor={`regra-${index}-id`} className="mb-1 block text-xs text-content-muted">
            Id
          </label>
          <input
            id={`regra-${index}-id`}
            value={regra.id}
            onChange={(e) => onChange(index, 'id', e.target.value)}
            placeholder="ex.: vigencia_dias"
            className="input-field w-full font-mono text-xs"
          />
        </div>
        <div>
          <label htmlFor={`regra-${index}-rotulo`} className="mb-1 block text-xs text-content-muted">
            Rótulo
          </label>
          <input
            id={`regra-${index}-rotulo`}
            value={regra.rotulo}
            onChange={(e) => onChange(index, 'rotulo', e.target.value)}
            placeholder="ex.: Vigência mínima"
            className="input-field w-full"
          />
        </div>
        <div>
          <label htmlFor={`regra-${index}-tipo`} className="mb-1 block text-xs text-content-muted">
            Tipo de âncora
          </label>
          <select
            id={`regra-${index}-tipo`}
            value={regra.tipo}
            onChange={(e) => onChange(index, 'tipo', e.target.value as AnchorTipo)}
            className="input-field w-full"
          >
            {TIPOS.map((t) => (
              <option key={t} value={t}>
                {ANCHOR_TIPO_LABELS[t]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={`regra-${index}-ancora`} className="mb-1 block text-xs text-content-muted">
            Âncora (texto ou item, ex.: &quot;vigência&quot;)
          </label>
          <input
            id={`regra-${index}-ancora`}
            value={regra.ancora || ''}
            onChange={(e) => onChange(index, 'ancora', e.target.value)}
            placeholder="Opcional — busca no documento todo"
            className="input-field w-full"
          />
        </div>

        {regra.tipo === 'booleano' && (
          <div className="sm:col-span-2">
            <label htmlFor={`regra-${index}-palavras`} className="mb-1 block text-xs text-content-muted">
              Palavras-chave (separadas por vírgula)
            </label>
            <input
              id={`regra-${index}-palavras`}
              value={(regra.palavras_chave || []).join(', ')}
              onChange={(e) => handlePalavras(e.target.value)}
              placeholder="ex.: garantia, caução"
              className="input-field w-full"
            />
          </div>
        )}

        {regra.tipo === 'legal' && (
          <div className="sm:col-span-2">
            <label htmlFor={`regra-${index}-regex`} className="mb-1 block text-xs text-content-muted">
              Regex da referência legal
            </label>
            <input
              id={`regra-${index}-regex`}
              value={regra.regex || ''}
              onChange={(e) => onChange(index, 'regex', e.target.value)}
              placeholder="ex.: 14\.133/2021"
              className="input-field w-full font-mono text-xs"
            />
          </div>
        )}

        {['numero_inteiro', 'numero_extenso'].includes(regra.tipo) && (
          <div>
            <label htmlFor={`regra-${index}-unidade`} className="mb-1 block text-xs text-content-muted">
              Unidade
            </label>
            <input
              id={`regra-${index}-unidade`}
              value={regra.unidade || ''}
              onChange={(e) => onChange(index, 'unidade', e.target.value)}
              placeholder="ex.: dias, meses"
              className="input-field w-full"
            />
          </div>
        )}
      </div>
    </div>
  );
}
