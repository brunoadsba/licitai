'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { listDocuments, deleteDocument } from '@/lib/api';
import type { DocumentResponse } from '@/types';
import { STATUS_LABELS } from '@/types';

export default function DashboardPage() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    try {
      setLoading(true);
      const data = await listDocuments();
      setDocuments(data.documents);
    } catch (err) {
      setError('Erro ao carregar documentos. Verifique se o backend está rodando.');
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Remover "${name}"? Esta ação não pode ser desfeita.`)) return;
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch {
      setError('Erro ao remover documento.');
    }
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function getStatusBadge(status: string) {
    const classes: Record<string, string> = {
      uploaded: 'badge-info',
      parsing: 'badge-medio',
      parsed: 'badge-baixo',
      analyzing: 'badge-medio',
      completed: 'badge-baixo',
      error: 'badge-critico',
    };
    return classes[status] || 'badge-info';
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Seus Documentos</h1>
          <p className="text-gray-400 mt-1 text-sm">
            Gerencie e analise seus Termos de Referência
          </p>
        </div>
        <Link href="/upload" className="btn-primary">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Enviar Documento
        </Link>
      </div>

      {/* Estatísticas rápidas */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Total', value: documents.length, color: 'from-primary-500/20 to-primary-600/10' },
          { label: 'Analisados', value: documents.filter((d) => d.status === 'completed').length, color: 'from-green-500/20 to-green-600/10' },
          { label: 'Pendentes', value: documents.filter((d) => d.status === 'parsed').length, color: 'from-yellow-500/20 to-yellow-600/10' },
          { label: 'Erros', value: documents.filter((d) => d.status === 'error').length, color: 'from-red-500/20 to-red-600/10' },
        ].map((stat) => (
          <div key={stat.label} className="glass-card p-5">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{stat.label}</p>
            <p className={`text-3xl font-bold bg-gradient-to-r ${stat.color} bg-clip-text text-transparent`}>
              {loading ? '—' : stat.value}
            </p>
          </div>
        ))}
      </div>

      {/* Mensagem de erro */}
      {error && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Lista de documentos */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-24" />
          ))}
        </div>
      ) : documents.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <svg className="w-16 h-16 mx-auto text-gray-600 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <h3 className="text-lg font-semibold text-gray-300 mb-2">Nenhum documento</h3>
          <p className="text-gray-500 mb-6 text-sm">
            Envie seu primeiro Termo de Referência para começar a análise.
          </p>
          <Link href="/upload" className="btn-primary">
            Enviar Documento
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map((doc, idx) => (
            <div
              key={doc.id}
              className="glass-card-interactive p-5 animate-slide-up"
              style={{ animationDelay: `${idx * 50}ms` }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  {/* Ícone do tipo */}
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
                    doc.file_type === 'pdf'
                      ? 'bg-red-500/10 text-red-400'
                      : 'bg-blue-500/10 text-blue-400'
                  }`}>
                    <span className="text-xs font-bold uppercase">{doc.file_type}</span>
                  </div>

                  {/* Info */}
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-white truncate">
                      {doc.filename_original}
                    </h3>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>{formatFileSize(doc.file_size_bytes)}</span>
                      <span>•</span>
                      <span>{doc.total_items} itens</span>
                      <span>•</span>
                      <span>{formatDate(doc.created_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Ações */}
                <div className="flex items-center gap-3 shrink-0 ml-4">
                  <span className={`badge ${getStatusBadge(doc.status)}`}>
                    {STATUS_LABELS[doc.status] || doc.status}
                  </span>

                  {doc.status === 'parsed' && (
                    <Link
                      href={`/analysis/${doc.id}`}
                      className="btn-primary text-xs px-4 py-2"
                    >
                      Analisar
                    </Link>
                  )}

                  {doc.status === 'completed' && (
                    <Link
                      href={`/analysis/${doc.id}`}
                      className="btn-secondary text-xs px-4 py-2"
                    >
                      Ver Resultado
                    </Link>
                  )}

                  <button
                    onClick={() => handleDelete(doc.id, doc.filename_original)}
                    className="p-2 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    title="Remover"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
