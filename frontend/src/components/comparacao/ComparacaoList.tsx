'use client';

import Link from 'next/link';
import { GitCompareArrows, MailCheck } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { COMPARACAO_STATUS_LABELS } from '@/types';

interface Comparacao {
  id: string;
  status: string;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  total_resultados: number;
  fornecedores: { id: string; nome: string }[];
}

interface ComparacaoListProps {
  comparacoes: Comparacao[];
  loading: boolean;
  sendingFeedbackId: string | null;
  feedbackEnviadosIds: string[];
  onFeedback: (id: string) => void;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function getStatusTone(status: string): 'medium' | 'low' | 'critical' | 'info' {
  const tones: Record<string, 'medium' | 'low' | 'critical' | 'info'> = {
    pending: 'medium',
    running: 'medium',
    completed: 'low',
    error: 'critical',
  };
  return tones[status] || 'info';
}

/**
 * Listagem de comparações realizadas com ações de feedback e acesso à matriz.
 */
export default function ComparacaoList({
  comparacoes,
  loading,
  sendingFeedbackId,
  feedbackEnviadosIds,
  onFeedback,
}: ComparacaoListProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    );
  }

  if (comparacoes.length === 0) {
    return (
      <div className="glass-card p-12 text-center">
        <p className="text-content-muted">Nenhuma comparação realizada ainda.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {comparacoes.map((cmp) => {
        const enviado = feedbackEnviadosIds.includes(cmp.id);
        return (
          <div key={cmp.id} className="glass-card-interactive p-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-3">
                  <span
                    className={`badge ${
                      { medium: 'badge-medio', low: 'badge-baixo', critical: 'badge-critico', info: 'badge-info' }[
                        getStatusTone(cmp.status)
                      ]
                    }`}
                  >
                    {COMPARACAO_STATUS_LABELS[cmp.status as keyof typeof COMPARACAO_STATUS_LABELS] || cmp.status}
                  </span>
                  <span className="tnum text-xs text-content-subtle">{formatDate(cmp.created_at)}</span>
                </div>
                <div className="tnum mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-content-subtle">
                  <span>{cmp.total_resultados} resultados</span>
                  {cmp.fornecedores.length > 0 && (
                    <>
                      <span aria-hidden>·</span>
                      <span>Fornecedores: {cmp.fornecedores.map((f) => f.nome).join(', ')}</span>
                    </>
                  )}
                </div>
              </div>
              {cmp.status === 'completed' && (
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onFeedback(cmp.id)}
                    disabled={sendingFeedbackId === cmp.id || enviado}
                  >
                    <MailCheck className="h-3.5 w-3.5" aria-hidden />
                    {sendingFeedbackId === cmp.id
                      ? 'Enviando…'
                      : enviado
                        ? 'Pendências Enviadas'
                        : 'Enviar Pendências'}
                  </Button>
                  <Link href={`/comparacao/${cmp.id}`}>
                    <Button variant="secondary" size="sm">
                      <GitCompareArrows className="h-3.5 w-3.5" aria-hidden />
                      Ver Matriz
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
