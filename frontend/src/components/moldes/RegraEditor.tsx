'use client';

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
    <div className="glass-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 uppercase tracking-wider">
          Regra {index + 1}
        </span>
        <button
          onClick={() => onRemove(index)}
          className="text-gray-600 hover:text-red-400 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Id</label>
          <input
            value={regra.id}
            onChange={(e) => onChange(index, 'id', e.target.value)}
            placeholder="ex.: vigencia_dias"
            className="input-field w-full"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Rótulo</label>
          <input
            value={regra.rotulo}
            onChange={(e) => onChange(index, 'rotulo', e.target.value)}
            placeholder="ex.: Vigência mínima"
            className="input-field w-full"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Tipo de âncora</label>
          <select
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
          <label className="block text-xs text-gray-500 mb-1">
            Âncora (texto ou item, ex.: &quot;vigência&quot;)
          </label>
          <input
            value={regra.ancora || ''}
            onChange={(e) => onChange(index, 'ancora', e.target.value)}
            placeholder="Opcional — busca no documento todo"
            className="input-field w-full"
          />
        </div>

        {regra.tipo === 'booleano' && (
          <div className="sm:col-span-2">
            <label className="block text-xs text-gray-500 mb-1">
              Palavras-chave (separadas por vírgula)
            </label>
            <input
              value={(regra.palavras_chave || []).join(', ')}
              onChange={(e) => handlePalavras(e.target.value)}
              placeholder="ex.: garantia, caução"
              className="input-field w-full"
            />
          </div>
        )}

        {regra.tipo === 'legal' && (
          <div className="sm:col-span-2">
            <label className="block text-xs text-gray-500 mb-1">
              Regex da referência legal
            </label>
            <input
              value={regra.regex || ''}
              onChange={(e) => onChange(index, 'regex', e.target.value)}
              placeholder="ex.: 14\.133/2021"
              className="input-field w-full"
            />
          </div>
        )}

        {['numero_inteiro', 'numero_extenso'].includes(regra.tipo) && (
          <div>
            <label className="block text-xs text-gray-500 mb-1">Unidade</label>
            <input
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
