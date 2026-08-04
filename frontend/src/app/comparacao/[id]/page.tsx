'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getComparacao, getMatriz } from '@/lib/api';
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

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const cmp = await getComparacao(comparacaoId);
      setComparacao(cmp);

      if (['completed', 'error'].includes(cmp.status)) {
        const m = await getMatriz(comparacaoId);
        setMatriz(m);
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar a comparação.');
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

    const interval = setInterval(async () => {
      try {
        const updated = await getComparacao(comparacaoId);
        setComparacao(updated);

        if (['completed', 'error'].includes(updated.status)) {
          clearInterval(interval);
          const m = await getMatriz(comparacaoId);
          setMatriz(m);
        }
      } catch {
        // silenciar erros de polling
      }
    }, 3000);

    return () => clearInterval(interval);
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
    return classes[status] || 'bg-gray-500/10 text-gray-300 border-gray-500/30';
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
      <div className="space-y-4 animate-fade-in">
        <div className="skeleton h-12 w-72" />
        <div className="skeleton h-96" />
      </div>
    );
  }

  if (!comparacao) {
    return (
      <div className="glass-card p-12 text-center">
        <p className="text-gray-400">Comparação não encontrada.</p>
        <Link href="/comparacao" className="btn-primary mt-4 inline-flex">
          Voltar
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
            <Link href="/" className="hover:text-gray-300 transition-colors">Painel</Link>
            <span>›</span>
            <Link href="/comparacao" className="hover:text-gray-300 transition-colors">
              Comparações
            </Link>
            <span>›</span>
            <span className="text-gray-400">Matriz de Conformidade</span>
          </div>
          <h1 className="text-xl font-bold text-white">Matriz de Conformidade</h1>
          <p className="text-gray-500 text-sm mt-1">
            Criada em {formatDate(comparacao.created_at)}
          </p>
        </div>
        <span className={`badge ${getStatusBadge(comparacao.status)}`}>
          {COMPARACAO_STATUS_LABELS[comparacao.status] || comparacao.status}
        </span>
      </div>

      {comparacao.status === 'error' && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-red-400 text-sm">
            {comparacao.error_message || 'Erro durante a comparação.'}
          </p>
        </div>
      )}

      {error && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Em execução */}
      {['pending', 'running'].includes(comparacao.status) && (
        <div className="glass-card p-8 text-center">
          <svg className="w-10 h-10 mx-auto text-primary-400 animate-spin mb-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-gray-300 font-medium">
            {COMPARACAO_STATUS_LABELS[comparacao.status]}
          </p>
          <p className="text-gray-500 text-sm mt-1">
            Comparando as propostas com o Termo de Referência...
          </p>
        </div>
      )}

      {/* Matriz */}
      {matriz && matriz.status === 'completed' && (
        <div className="glass-card p-6 overflow-x-auto">
          <div className="flex items-center gap-4 mb-6 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-xs text-gray-400">OK</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-yellow-500" />
              <span className="text-xs text-gray-400">ATENÇÃO</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500" />
              <span className="text-xs text-gray-400">FALHA</span>
            </div>
          </div>

          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left p-3 text-xs text-gray-500 uppercase tracking-wider border-b border-white/[0.06] min-w-[220px]">
                  Regra
                </th>
                {matriz.fornecedores.map((f) => (
                  <th
                    key={f.id}
                    className="text-center p-3 text-xs text-gray-400 uppercase tracking-wider border-b border-white/[0.06] min-w-[140px]"
                  >
                    {f.nome}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matriz.linhas.map((linha) => (
                <tr key={linha.regra_id} className="hover:bg-white/[0.02]">
                  <td className="p-3 border-b border-white/[0.04] align-top">
                    <p className="font-medium text-gray-200">{linha.rotulo}</p>
                    <p className="text-[11px] text-gray-600 font-mono mt-0.5">
                      {linha.regra_id}
                    </p>
                  </td>
                  {linha.celulas.map((celula) => (
                    <td
                      key={celula.fornecedor_id}
                      className={`p-3 border-b border-white/[0.04] text-center align-top border ${getCellColors(celula.status)} rounded-xl`}
                    >
                      <span className={`badge ${getCellBadge(celula.status)}`}>
                        {CONFORMIDADE_LABELS[celula.status] || celula.status}
                      </span>
                      {celula.motivo && (
                        <p className="text-[11px] mt-2 leading-snug text-gray-400">
                          {celula.motivo}
                        </p>
                      )}
                      {(celula.valor_tr || celula.valor_proposta) && (
                        <div className="mt-2 text-[11px] text-gray-500">
                          <p>TR: <span className="text-gray-300">{celula.valor_tr || '—'}</span></p>
                          <p>Proposta: <span className="text-gray-300">{celula.valor_proposta || '—'}</span></p>
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
