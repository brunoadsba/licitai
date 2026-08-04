'use client';

import { useEffect, useState } from 'react';
import { listDocuments, diffDocuments } from '@/lib/api';

export default function DiffVersoesPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [docAntigoId, setDocAntigoId] = useState<string>('');
  const [docNovoId, setDocNovoId] = useState<string>('');
  const [diffing, setDiffing] = useState(false);
  const [diffResult, setDiffResult] = useState<any | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await listDocuments();
        const trs = res.documents.filter((d: any) => d.document_type === 'tr');
        setDocuments(trs);
        if (trs.length >= 2) {
          setDocAntigoId(trs[1].id);
          setDocNovoId(trs[0].id);
        } else if (trs.length === 1) {
          setDocAntigoId(trs[0].id);
          setDocNovoId(trs[0].id);
        }
      } catch {
        setError('Erro ao carregar lista de documentos TR.');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  async function handleCompare() {
    if (!docAntigoId || !docNovoId) {
      setError('Selecione os dois documentos para comparação.');
      return;
    }
    try {
      setDiffing(true);
      setError(null);
      const result = await diffDocuments(docAntigoId, docNovoId);
      setDiffResult(result);
    } catch (err: any) {
      setError(err.message || 'Erro ao comparar versões do TR.');
    } finally {
      setDiffing(false);
    }
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case 'inalterado':
        return 'badge-info';
      case 'alterado':
        return 'badge-warning';
      case 'adicionado':
        return 'badge-success';
      case 'removido':
        return 'badge-danger';
      default:
        return 'badge';
    }
  }

  return (
    <div className="space-y-8 animate-fade-in max-w-6xl mx-auto">
      {/* Cabeçalho */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <span>🔄</span> Comparador de Versões de TR
        </h1>
        <p className="text-gray-400 mt-1 text-sm">
          Alinhamento inteligente item por item para identificar acréscimos, exclusões e alterações de texto entre duas versões do Termo de Referência.
        </p>
      </div>

      {error && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Card de Seleção */}
      <div className="glass-card p-6 space-y-4">
        <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
          Selecione as Versões para Comparação
        </h2>

        {loading ? (
          <div className="skeleton h-12" />
        ) : documents.length < 2 ? (
          <p className="text-amber-400 text-sm">
            É necessário ter pelo menos 2 documentos TR cadastrados no sistema para comparar versões.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1 font-medium">
                📄 Versão Original (Antiga):
              </label>
              <select
                value={docAntigoId}
                onChange={(e) => setDocAntigoId(e.target.value)}
                className="input-field w-full text-sm bg-surface-900"
              >
                {documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.filename_original} ({d.total_items} itens) — {new Date(d.created_at).toLocaleDateString('pt-BR')}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-gray-400 mb-1 font-medium">
                📄 Nova Versão (Revisada):
              </label>
              <select
                value={docNovoId}
                onChange={(e) => setDocNovoId(e.target.value)}
                className="input-field w-full text-sm bg-surface-900"
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
          <button
            onClick={handleCompare}
            disabled={diffing || documents.length < 2 || docAntigoId === docNovoId}
            className="btn-primary"
          >
            {diffing ? 'Comparando...' : 'Comparar Versões'}
          </button>
        </div>
      </div>

      {/* Resultado do Diff */}
      {diffResult && (
        <div className="space-y-6">
          {/* Resumo da comparação */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="glass-card p-4 text-center">
              <p className="text-xs text-gray-400">Total de Itens</p>
              <p className="text-2xl font-bold text-white mt-1">{diffResult.total}</p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-xs text-amber-400 font-medium">Alterados</p>
              <p className="text-2xl font-bold text-amber-400 mt-1">{diffResult.resumo?.alterados || 0}</p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-xs text-green-400 font-medium">Adicionados</p>
              <p className="text-2xl font-bold text-green-400 mt-1">{diffResult.resumo?.adicionados || 0}</p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-xs text-red-400 font-medium">Removidos</p>
              <p className="text-2xl font-bold text-red-400 mt-1">{diffResult.resumo?.removidos || 0}</p>
            </div>
          </div>

          {/* Lista de Itens comparados */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-white">Detalhamento das Alterações</h2>

            {diffResult.itens.map((item: any) => (
              <div key={item.item_number} className="glass-card p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm text-primary-400 font-bold">
                      Item {item.item_number}
                    </span>
                    {item.titulo && (
                      <h3 className="text-sm font-semibold text-white truncate max-w-md">
                        {item.titulo}
                      </h3>
                    )}
                  </div>
                  <span className={`badge ${getStatusBadge(item.status)} uppercase text-[10px]`}>
                    {item.status}
                  </span>
                </div>

                {/* Exibição do diff textual */}
                {item.status === 'alterado' && (
                  <div className="space-y-2 pt-2">
                    <div className="diff-removed">
                      <p className="text-xs text-red-400/70 font-semibold uppercase tracking-wider mb-1">Versão Anterior</p>
                      <p className="text-sm text-red-300/90 whitespace-pre-wrap">{item.conteudo_antes}</p>
                    </div>
                    <div className="diff-added">
                      <p className="text-xs text-green-400/70 font-semibold uppercase tracking-wider mb-1">Nova Versão</p>
                      <p className="text-sm text-green-300/90 whitespace-pre-wrap">{item.conteudo_depois}</p>
                    </div>
                  </div>
                )}

                {item.status === 'adicionado' && (
                  <div className="diff-added">
                    <p className="text-xs text-green-400/70 font-semibold uppercase tracking-wider mb-1">Novo Item Adicionado</p>
                    <p className="text-sm text-green-300/90 whitespace-pre-wrap">{item.conteudo_depois}</p>
                  </div>
                )}

                {item.status === 'removido' && (
                  <div className="diff-removed">
                    <p className="text-xs text-red-400/70 font-semibold uppercase tracking-wider mb-1">Item Excluído</p>
                    <p className="text-sm text-red-300/90 whitespace-pre-wrap">{item.conteudo_antes}</p>
                  </div>
                )}

                {item.status === 'inalterado' && (
                  <p className="text-xs text-gray-500 italic">Item idêntico em ambas as versões.</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
