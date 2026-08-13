import Link from 'next/link';
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
  onFeedback: (id: string) => void;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function getStatusBadge(status: string) {
  const classes: Record<string, string> = {
    pending: 'badge-medio',
    running: 'badge-medio',
    completed: 'badge-baixo',
    error: 'badge-critico',
  };
  return classes[status] || 'badge-info';
}

/**
 * Listagem de comparações realizadas com ações de feedback e acesso à matriz.
 */
export default function ComparacaoList({
  comparacoes,
  loading,
  sendingFeedbackId,
  onFeedback,
}: ComparacaoListProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="skeleton h-20" />
        ))}
      </div>
    );
  }

  if (comparacoes.length === 0) {
    return (
      <div className="glass-card p-12 text-center">
        <p className="text-gray-500">Nenhuma comparação realizada ainda.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {comparacoes.map((cmp) => (
        <div key={cmp.id} className="glass-card-interactive p-5">
          <div className="flex items-center justify-between">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-3">
                <span className={`badge ${getStatusBadge(cmp.status)}`}>
                  {COMPARACAO_STATUS_LABELS[cmp.status as keyof typeof COMPARACAO_STATUS_LABELS] || cmp.status}
                </span>
                <span className="text-xs text-gray-500">
                  {formatDate(cmp.created_at)}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-gray-500">
                <span>{cmp.total_resultados} resultados</span>
                {cmp.fornecedores.length > 0 && (
                  <>
                    <span>•</span>
                    <span>
                      Fornecedores:{' '}
                      {cmp.fornecedores.map((f) => f.nome).join(', ')}
                    </span>
                  </>
                )}
              </div>
            </div>
            {cmp.status === 'completed' && (
              <div className="flex items-center gap-2 shrink-0 ml-4">
                <button
                  onClick={() => onFeedback(cmp.id)}
                  disabled={sendingFeedbackId === cmp.id}
                  className="btn-secondary text-xs px-4 py-2"
                >
                  {sendingFeedbackId === cmp.id ? 'Enviando...' : 'Enviar Pendências'}
                </button>
                <Link
                  href={`/comparacao/${cmp.id}`}
                  className="btn-secondary text-xs px-4 py-2"
                >
                  Ver Matriz
                </Link>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
