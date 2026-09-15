'use client';

import Link from 'next/link';
import { FileText } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import type { DocumentResponse } from '@/types';

interface Props {
  documents: DocumentResponse[];
  loading: boolean;
  docAntigoId: string;
  docNovoId: string;
  diffing: boolean;
  onChangeAntigo: (id: string) => void;
  onChangeNovo: (id: string) => void;
  onCompare: () => void;
}

export default function VersoesSelector({
  documents,
  loading,
  docAntigoId,
  docNovoId,
  diffing,
  onChangeAntigo,
  onChangeNovo,
  onCompare,
}: Props) {
  return (
    <div className="glass-card space-y-4 p-5 sm:p-6">
      <h2 className="text-[11px] font-medium uppercase tracking-widest text-content-subtle">
        Selecione as versões para comparação
      </h2>

      {loading ? (
        <Skeleton className="h-12" />
      ) : documents.length < 2 ? (
        <EmptyState
          icon={FileText}
          title="Poucos TRs para comparar"
          description="Cadastre pelo menos dois Termos de Referência no Painel para comparar versões."
          action={
            <Link href="/upload">
              <Button>Enviar TR</Button>
            </Link>
          }
          className="py-10"
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label htmlFor="versao-antiga" className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-content-muted">
              <FileText className="h-3.5 w-3.5 text-content-subtle" aria-hidden />
              Versão Original (Antiga)
            </label>
            <select
              id="versao-antiga"
              value={docAntigoId}
              onChange={(e) => onChangeAntigo(e.target.value)}
              className="input-field tnum w-full text-sm"
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename_original} ({d.total_items} itens) — {new Date(d.created_at).toLocaleDateString('pt-BR')}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="versao-nova" className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-content-muted">
              <FileText className="h-3.5 w-3.5 text-accent-400" aria-hidden />
              Nova Versão (Revisada)
            </label>
            <select
              id="versao-nova"
              value={docNovoId}
              onChange={(e) => onChangeNovo(e.target.value)}
              className="input-field tnum w-full text-sm"
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename_original} ({d.total_items} itens) — {new Date(d.created_at).toLocaleDateString('pt-BR')}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      <div className="pt-2">
        <Button onClick={onCompare} loading={diffing} disabled={diffing || documents.length < 2 || docAntigoId === docNovoId}>
          {diffing ? 'Comparando…' : 'Comparar Versões'}
        </Button>
      </div>
    </div>
  );
}
