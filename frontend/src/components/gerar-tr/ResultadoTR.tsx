'use client';

import { useRouter } from 'next/navigation';

interface ResultadoTRProps {
  resultado: {
    filename_original: string;
    total_itens: number;
    document_id: string;
    itens: { item_number: string; title: string; content: string }[];
    html_completo?: string;
  };
  onCopiarHtml: () => void;
  onRecomecar: () => void;
}

/**
 * Passo 3 do assistente: resultado da geração com cópia HTML para o SEI.
 */
export default function ResultadoTR({ resultado, onCopiarHtml, onRecomecar }: ResultadoTRProps) {
  const router = useRouter();

  return (
    <div className="space-y-6">
      <div className="glass-card p-6 border-green-500/30 space-y-4">
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div>
            <span className="badge badge-success text-[10px] uppercase">Geração Concluída</span>
            <h2 className="text-xl font-bold text-white mt-1">{resultado.filename_original}</h2>
            <p className="text-xs text-gray-400">Total de {resultado.total_itens} seções geradas com fundamentação no TCU</p>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={onCopiarHtml} className="btn-primary text-xs">
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
          {resultado.itens.map((item) => (
            <div key={item.item_number} className="p-4 bg-surface-900/60 rounded-xl border border-white/10 space-y-2">
              <span className="font-mono text-xs font-bold text-primary-400">{item.item_number} {item.title}</span>
              <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">{item.content}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-start">
        <button onClick={onRecomecar} className="btn-secondary">
          🔄 Criar Outro Termo de Referência
        </button>
      </div>
    </div>
  );
}
