'use client';

import { useRouter } from 'next/navigation';
import { ClipboardCopy, RotateCcw, SearchCheck } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

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
      <div className="glass-card space-y-4 border-green-500/30 p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line-subtle pb-3">
          <div>
            <Badge tone="low" className="text-[10px]">
              Geração Concluída
            </Badge>
            <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-content-primary">
              {resultado.filename_original}
            </h2>
            <p className="tnum mt-0.5 text-xs text-content-muted">
              Total de {resultado.total_itens} seções geradas com fundamentação no TCU
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" onClick={onCopiarHtml}>
              <ClipboardCopy className="h-3.5 w-3.5" aria-hidden />
              Copiar HTML para SEI
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => router.push(`/analysis/${resultado.document_id}`)}
            >
              <SearchCheck className="h-3.5 w-3.5" aria-hidden />
              Auditar no LicitAI
            </Button>
          </div>
        </div>

        {/* Exibição das seções geradas */}
        <div className="max-h-[600px] space-y-4 overflow-y-auto pr-2">
          {resultado.itens.map((item) => (
            <div
              key={item.item_number}
              className="space-y-2 rounded-xl border border-line-subtle bg-canvas/60 p-4"
            >
              <span className="tnum font-mono text-xs font-semibold text-accent-400">
                {item.item_number} {item.title}
              </span>
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-content-secondary">
                {item.content}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-start">
        <Button onClick={onRecomecar} variant="secondary">
          <RotateCcw className="h-4 w-4" aria-hidden />
          Criar Outro Termo de Referência
        </Button>
      </div>
    </div>
  );
}
