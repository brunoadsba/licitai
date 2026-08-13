import type { DocumentItemResponse, CorrectionResponse } from '@/types';
import { useCopy } from '@/lib/useCopy';
import CorrectionCard from '@/components/analysis/CorrectionCard';

interface ItemDetailProps {
  item: DocumentItemResponse;
  corrections: CorrectionResponse[];
  getUpdatedItemText: (item: DocumentItemResponse, corrections: CorrectionResponse[]) => string;
  showCorrections?: boolean;
}

/**
 * Detalhe do item selecionado: conteúdo original, cópia do item corrigido (SEI) e correções DE → PARA.
 */
export default function ItemDetail({ item, corrections, getUpdatedItemText, showCorrections = true }: ItemDetailProps) {
  const { copy, isCopied } = useCopy();
  const showCopyItem = showCorrections && corrections.length > 0;

  return (
    <div className="col-span-8 space-y-4">
      {/* Conteúdo do item */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-sm font-mono text-primary-400 font-semibold">
            {item.item_number}
          </span>
          {item.title && (
            <h3 className="text-lg font-semibold text-white">
              {item.title}
            </h3>
          )}
          <span className="badge badge-info text-[10px] ml-auto">
            {item.item_type}
          </span>
        </div>

        <div className="bg-surface-900/50 rounded-xl p-4 max-h-48 overflow-y-auto mb-4">
          <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
            {item.content}
          </p>
        </div>

        {/* Ação de Copiar Item Inteiro Atualizado (para o SEI) */}
        {showCopyItem && (
          <div className="flex items-center justify-between pt-3 border-t border-white/[0.06]">
            <span className="text-xs text-gray-400">
              💡 Copie o item completo pronto para o SEI (com correções aplicadas):
            </span>
            <button
              onClick={() =>
                copy(getUpdatedItemText(item, corrections), `item_full_${item.id}`)
              }
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary-600/20 hover:bg-primary-600/30 text-primary-300 border border-primary-500/30 flex items-center gap-1.5 transition-all"
            >
              {isCopied(`item_full_${item.id}`) ? (
                <>
                  <svg className="w-3.5 h-3.5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  Copiado!
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.757c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                  </svg>
                  Copiar Item Inteiro para o SEI
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Correções do item */}
      {showCorrections && (corrections.length === 0 ? (
        <div className="glass-card p-6 text-center">
          <svg className="w-10 h-10 mx-auto text-green-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-green-400 font-medium text-sm">Item adequado</p>
          <p className="text-gray-500 text-xs mt-1">
            Nenhuma correção necessária. Não é preciso alterar este item no SEI.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {corrections.map((correction, idx) => (
            <CorrectionCard key={correction.id} correction={correction} index={idx} />
          ))}
        </div>
      ))}
    </div>
  );
}
