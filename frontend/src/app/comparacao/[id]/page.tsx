'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, LoaderCircle } from 'lucide-react';
import { getComparacao, getMatriz, extractErrorMessage } from '@/lib/api';
import { startPolling } from '@/lib/polling';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  COMPARACAO_STATUS_LABELS,
  CONFORMIDADE_LABELS,
} from '@/types';
import type {
  ComparacaoResponse,
  MatrizResponse,
  ConformidadeStatus,
} from '@/types';

export default function MatrizPage() {
  const params = useParams();
  const comparacaoId = params.id as string;

  const [comparacao, setComparacao] = useState<ComparacaoResponse | null>(null);
  const [matriz, setMatriz] = useState<MatrizResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pollingError, setPollingError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const cmp = await getComparacao(comparacaoId);
      setComparacao(cmp);

      if (['completed', 'error'].includes(cmp.status)) {
        const m = await getMatriz(comparacaoId);
        setMatriz(m);
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao carregar a comparação.'));
    } finally {
      setLoading(false);
    }
  }, [comparacaoId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Polling durante execução
  useEffect(() => {
    if (!comparacao || !['pending', 'running'].includes(comparacao.status)) return;

    const { cancel } = startPolling(
      () => getComparacao(comparacaoId, { skipCache: true }),
      (updated) => ['completed', 'error'].includes(updated.status),
      {
        initialIntervalMs: 3000,
        maxIntervalMs: 15_000,
        deadlineMs: 30 * 60 * 1000,
        maxFailures: 8,
        onResult: (updated) => {
          setComparacao(updated);
          setPollingError(null);
          if (['completed', 'error'].includes(updated.status)) {
            void getMatriz(comparacaoId).then(setMatriz).catch(() => {
              /* matriz pode falhar; status já atualizado */
            });
            return true;
          }
        },
        onError: (err, failures) => {
          if (failures >= 2) {
            setPollingError(
              `${extractErrorMessage(err, 'Falha ao atualizar status.')} Verificando novamente…`
            );
          }
        },
      }
    );

    return () => cancel();
    // Intencional: reagir só a mudança de status, não a cada tick
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [comparacao?.status, comparacaoId]);

  function getStatusBadge(status: string) {
    const classes: Record<string, string> = {
      pending: 'badge-medio',
      running: 'badge-medio',
      completed: 'badge-baixo',
      error: 'badge-critico',
    };
    return classes[status] || 'badge-info';
  }

  function getCellBadge(status: ConformidadeStatus) {
    const classes: Record<string, string> = {
      ok: 'badge-baixo',
      falha: 'badge-critico',
      atencao: 'badge-medio',
    };
    return classes[status] || 'badge-info';
  }

  function getCellColors(status: ConformidadeStatus) {
    const classes: Record<string, string> = {
      ok: 'bg-green-500/10 text-green-300 border-green-500/30',
      falha: 'bg-red-500/10 text-red-300 border-red-500/30',
      atencao: 'bg-yellow-500/10 text-yellow-300 border-yellow-500/30',
    };
    return classes[status] || 'bg-white/[0.04] text-content-secondary border-line-subtle';
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }

  if (loading) {
    return (
      <div className="animate-fade-in space-y-4">
        <Skeleton className="h-12 w-72" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (!comparacao) {
    return (
      <div className="glass-card p-12 text-center">
        <p className="text-content-muted">Comparação não encontrada.</p>
        <Link href="/comparacao" className="btn-primary mt-4 inline-flex">
          Voltar
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      {/* Cabeçalho */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="mb-1 flex items-center gap-1.5 text-xs text-content-subtle">
            <Link
              href="/"
              className="inline-flex items-center gap-0.5 outline-none transition-colors hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
            >
              <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
              Painel
            </Link>
            <span aria-hidden>/</span>
            <Link
              href="/comparacao"
              className="outline-none transition-colors hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
            >
              Comparações
            </Link>
            <span aria-hidden>/</span>
            <span className="text-content-muted">Matriz de Conformidade</span>
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-content-primary sm:text-2xl">
            Matriz de Conformidade
          </h1>
          <p className="tnum mt-1 text-sm text-content-muted">
            Criada em {formatDate(comparacao.created_at)}
          </p>
        </div>
        <span className={`badge ${getStatusBadge(comparacao.status)}`}>
          {COMPARACAO_STATUS_LABELS[comparacao.status] || comparacao.status}
        </span>
      </div>

      {comparacao.status === 'error' && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-sm text-red-400">
            {comparacao.error_message || 'Erro durante a comparação.'}
          </p>
        </div>
      )}

      {pollingError && (
        <div className="glass-card border-yellow-500/20 p-4">
          <p className="text-sm text-yellow-400">{pollingError}</p>
        </div>
      )}

      {error && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Em execução */}
      {['pending', 'running'].includes(comparacao.status) && (
        <div className="glass-card p-8 text-center">
          <LoaderCircle
            className="mx-auto mb-4 h-10 w-10 animate-spin text-accent-400"
            aria-hidden
          />
          <p className="font-medium text-content-primary">
            {COMPARACAO_STATUS_LABELS[comparacao.status]}
          </p>
          <p className="mt-1 text-sm text-content-muted">
            Comparando as propostas com o Termo de Referência…
          </p>
        </div>
      )}

      {/* Matriz */}
      {matriz && matriz.status === 'completed' && (
        <div className="glass-card overflow-x-auto p-4 sm:p-6">
          <div className="mb-6 flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-green-500" aria-hidden />
              <span className="text-xs text-content-muted">OK</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-yellow-500" aria-hidden />
              <span className="text-xs text-content-muted">ATENÇÃO</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-red-500" aria-hidden />
              <span className="text-xs text-content-muted">FALHA</span>
            </div>
          </div>

          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="min-w-[200px] border-b border-line-subtle p-3 text-left text-[11px] uppercase tracking-widest text-content-subtle">
                  Regra
                </th>
                {matriz.fornecedores.map((f) => (
                  <th
                    key={f.id}
                    className="min-w-[140px] border-b border-line-subtle p-3 text-center text-[11px] uppercase tracking-widest text-content-muted"
                  >
                    {f.nome}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matriz.linhas.map((linha) => (
                <tr key={linha.regra_id} className="hover:bg-white/[0.02]">
                  <td className="border-b border-line-subtle p-3 align-top">
                    <p className="font-medium text-content-primary">{linha.rotulo}</p>
                    <p className="tnum mt-0.5 font-mono text-[11px] text-content-subtle">
                      {linha.regra_id}
                    </p>
                  </td>
                  {linha.celulas.map((celula) => (
                    <td
                      key={celula.fornecedor_id}
                      className={`rounded-xl border p-3 text-center align-top border-b border-b-white/[0.04] ${getCellColors(celula.status)}`}
                    >
                      <span className={`badge ${getCellBadge(celula.status)}`}>
                        {CONFORMIDADE_LABELS[celula.status] || celula.status}
                      </span>
                      {celula.motivo && (
                        <p className="mt-2 text-[11px] leading-snug text-content-muted">
                          {celula.motivo}
                        </p>
                      )}
                      {(celula.valor_tr || celula.valor_proposta) && (
                        <div className="tnum mt-2 space-y-0.5 text-[11px] text-content-subtle">
                          <p>
                            TR: <span className="text-content-secondary">{celula.valor_tr || '—'}</span>
                          </p>
                          <p>
                            Proposta:{' '}
                            <span className="text-content-secondary">{celula.valor_proposta || '—'}</span>
                          </p>
                        </div>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
