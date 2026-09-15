'use client';

import Link from 'next/link';
import { Badge } from '@/components/ui/Badge';
import type { Tone } from '@/components/ui/Badge';
import type { DiffItemResponse } from '@/types';
import { Button } from '@/components/ui/Button';

interface DiffResult {
  total: number;
  resumo?: { alterados?: number; adicionados?: number; removidos?: number };
  itens: DiffItemResponse[];
}

function getStatusTone(status: string): Tone {
  switch (status) {
    case 'inalterado':
      return 'neutral';
    case 'alterado':
      return 'medium';
    case 'adicionado':
      return 'low';
    case 'removido':
      return 'critical';
    default:
      return 'neutral';
  }
}

export default function VersoesDiffResult({
  diffResult,
  docAntigoId,
  docNovoId,
}: {
  diffResult: DiffResult;
  docAntigoId: string;
  docNovoId: string;
}) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="glass-card p-4 text-center">
          <p className="text-xs text-content-muted">Total de Itens</p>
          <p className="tnum mt-1 text-2xl font-semibold tracking-tight text-content-primary">{diffResult.total}</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-xs font-medium text-amber-400">Alterados</p>
          <p className="tnum mt-1 text-2xl font-semibold tracking-tight text-amber-400">{diffResult.resumo?.alterados || 0}</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-xs font-medium text-green-400">Adicionados</p>
          <p className="tnum mt-1 text-2xl font-semibold tracking-tight text-green-400">{diffResult.resumo?.adicionados || 0}</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-xs font-medium text-red-400">Removidos</p>
          <p className="tnum mt-1 text-2xl font-semibold tracking-tight text-red-400">{diffResult.resumo?.removidos || 0}</p>
        </div>
      </div>

      {docNovoId && docAntigoId && (
        <div className="glass-card flex flex-wrap items-center justify-between gap-3 border-accent-500/20 p-4">
          <div>
            <p className="text-sm font-medium text-content-primary">Próximo passo</p>
            <p className="text-xs text-content-muted">Analise a versão nova e revise só os achados prioritários antes de colar no SEI.</p>
          </div>
          <Link href={`/analysis/${docNovoId}?diffFrom=${encodeURIComponent(docAntigoId)}`}>
            <Button size="sm">Revisar versão nova</Button>
          </Link>
        </div>
      )}

      <div className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight text-content-primary">Detalhamento das Alterações</h2>

        {diffResult.itens.map((item) => (
          <div key={item.item_number} className="glass-card space-y-3 p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-3">
                <span className="tnum font-mono text-sm font-semibold text-accent-400">Item {item.item_number}</span>
                {item.titulo && <h3 className="max-w-md truncate text-sm font-semibold text-content-primary">{item.titulo}</h3>}
              </div>
              <Badge tone={getStatusTone(item.status)} className="uppercase text-[10px]">{item.status}</Badge>
            </div>

            {item.status === 'alterado' && (
              <div className="space-y-2 pt-2">
                <div className="diff-removed">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-red-400/70">Versão Anterior</p>
                  <p className="whitespace-pre-wrap text-sm text-red-300/90">{item.conteudo_antes}</p>
                </div>
                <div className="diff-added">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-green-400/70">Nova Versão</p>
                  <p className="whitespace-pre-wrap text-sm text-green-300/90">{item.conteudo_depois}</p>
                </div>
              </div>
            )}

            {item.status === 'adicionado' && (
              <div className="diff-added">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-green-400/70">Novo Item Adicionado</p>
                <p className="whitespace-pre-wrap text-sm text-green-300/90">{item.conteudo_depois}</p>
              </div>
            )}

            {item.status === 'removido' && (
              <div className="diff-removed">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-red-400/70">Item Excluído</p>
                <p className="whitespace-pre-wrap text-sm text-red-300/90">{item.conteudo_antes}</p>
              </div>
            )}

            {item.status === 'inalterado' && <p className="text-xs italic text-content-subtle">Item idêntico em ambas as versões.</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
