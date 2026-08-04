'use client';

import { useEffect, useState, useCallback } from 'react';
import { listRevisions, createRevision, restoreRevision } from '@/lib/api';

interface RevisionsTimelineModalProps {
  documentId: string;
  isOpen: boolean;
  onClose: () => void;
  onRestored: () => void;
}

export default function RevisionsTimelineModal({
  documentId,
  isOpen,
  onClose,
  onRestored,
}: RevisionsTimelineModalProps) {
  const [revisions, setRevisions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Formulário para novo snapshot
  const [rotulo, setRotulo] = useState('');
  const [descricao, setDescricao] = useState('');
  const [saving, setSaving] = useState(false);
  const [restoringVersao, setRestoringVersao] = useState<number | null>(null);

  const loadRevisionsList = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await listRevisions(documentId);
      setRevisions(res.revisions);
    } catch {
      setError('Erro ao carregar histórico de versões do documento.');
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    if (isOpen) {
      loadRevisionsList();
    }
  }, [isOpen, loadRevisionsList]);

  async function handleCreateRevision() {
    if (!rotulo.trim()) {
      setError('Informe um rótulo para a versão.');
      return;
    }
    try {
      setSaving(true);
      setError(null);
      await createRevision(documentId, rotulo.trim(), descricao.trim() || undefined);
      setRotulo('');
      setDescricao('');
      await loadRevisionsList();
    } catch (err: any) {
      setError(err.message || 'Erro ao criar versão snapshot.');
    } finally {
      setSaving(false);
    }
  }

  async function handleRestore(versao: number, rotuloVersao: string) {
    if (!window.confirm(`Deseja restaurar os itens do documento para a versão ${versao} ('${rotuloVersao}')?`)) {
      return;
    }
    try {
      setRestoringVersao(versao);
      setError(null);
      await restoreRevision(documentId, versao);
      onRestored();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Erro ao restaurar versão.');
    } finally {
      setRestoringVersao(null);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card max-w-2xl w-full p-6 space-y-5 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <span>🕒</span> Histórico de Edições (Versionamento Single-User)
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Linha do tempo de rascunhos e versões do documento
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-lg font-bold"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-400">
            {error}
          </div>
        )}

        {/* Criar Novo Snapshot */}
        <div className="bg-surface-900/60 p-4 rounded-xl border border-white/10 space-y-3">
          <h4 className="text-xs font-semibold text-gray-200 uppercase tracking-wider">
            ➕ Salvar Novo Snapshot / Rascunho Atual
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              value={rotulo}
              onChange={(e) => setRotulo(e.target.value)}
              placeholder="Rótulo da Versão (ex: Revisão Jurídica 1)"
              className="input-field text-xs bg-surface-900"
            />
            <input
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Descrição ou observações (opcional)"
              className="input-field text-xs bg-surface-900"
            />
          </div>
          <button
            onClick={handleCreateRevision}
            disabled={saving || !rotulo.trim()}
            className="btn-primary text-xs py-2 px-4"
          >
            {saving ? 'Salva...' : 'Salvar Snapshot'}
          </button>
        </div>

        {/* Linha do Tempo de Versões */}
        <div className="space-y-3">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Linha do Tempo de Versões Salvas
          </h4>

          {loading ? (
            <div className="skeleton h-20" />
          ) : revisions.length === 0 ? (
            <div className="text-center p-6 bg-surface-900/40 rounded-xl border border-white/5">
              <p className="text-xs text-gray-500">
                Nenhum snapshot historizado ainda. Crie o primeiro acima para salvar o estado atual do documento.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {revisions.map((rev) => (
                <div
                  key={rev.id}
                  className="p-4 bg-surface-900/60 rounded-xl border border-white/10 flex items-center justify-between gap-4"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="badge badge-info text-[10px] uppercase font-mono">
                        v{rev.versao}
                      </span>
                      <span className="text-sm font-semibold text-white truncate">
                        {rev.rotulo}
                      </span>
                    </div>
                    {rev.descricao && (
                      <p className="text-xs text-gray-400 truncate">{rev.descricao}</p>
                    )}
                    <p className="text-[10px] text-gray-500">
                      {new Date(rev.created_at).toLocaleString('pt-BR')} — {rev.items_snapshot.length} itens salvos
                    </p>
                  </div>

                  <button
                    onClick={() => handleRestore(rev.versao, rev.rotulo)}
                    disabled={restoringVersao === rev.versao}
                    className="btn-secondary text-xs shrink-0 py-1.5 px-3 hover:border-amber-500/50 hover:text-amber-300"
                  >
                    {restoringVersao === rev.versao ? 'Restaurando...' : 'Restaurar esta Versão'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
