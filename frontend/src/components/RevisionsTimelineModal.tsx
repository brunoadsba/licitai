'use client';

import { useEffect, useState, useCallback } from 'react';
import { History, Plus } from 'lucide-react';
import { listRevisions, createRevision, restoreRevision, extractErrorMessage } from '@/lib/api';
import type { DocumentRevision } from '@/types';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import ConfirmDialog from '@/components/ui/ConfirmDialog';

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
  const [revisions, setRevisions] = useState<DocumentRevision[]>([]);
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
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao criar versão snapshot.'));
    } finally {
      setSaving(false);
    }
  }

  const [restoreConfirm, setRestoreConfirm] = useState<{ versao: number; rotulo: string } | null>(null);

  async function handleRestore(versao: number, rotuloVersao: string) {
    try {
      setRestoringVersao(versao);
      setError(null);
      await restoreRevision(documentId, versao);
      onRestored();
      onClose();
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao restaurar versão.'));
    } finally {
      setRestoringVersao(null);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(next) => (!next ? onClose() : undefined)}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <History className="h-5 w-5 text-accent-400" aria-hidden />
            Histórico de Edições
          </DialogTitle>
          <DialogDescription>
            Linha do tempo de rascunhos e versões do documento (versionamento single-user).
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
            {error}
          </div>
        )}

        {/* Criar Novo Snapshot */}
        <div className="space-y-3 rounded-xl border border-line-strong bg-canvas/60 p-4">
          <h4 className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-widest text-content-subtle">
            <Plus className="h-3.5 w-3.5" aria-hidden />
            Salvar novo snapshot do estado atual
          </h4>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              value={rotulo}
              onChange={(e) => setRotulo(e.target.value)}
              placeholder="Rótulo da versão (ex: Revisão Jurídica 1)"
              aria-label="Rótulo da versão"
              className="input-field text-xs"
            />
            <input
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Descrição ou observações (opcional)"
              aria-label="Descrição da versão"
              className="input-field text-xs"
            />
          </div>
          <Button onClick={handleCreateRevision} disabled={saving || !rotulo.trim()} loading={saving} size="sm">
            {saving ? 'Salvando…' : 'Salvar Snapshot'}
          </Button>
        </div>

        {/* Linha do Tempo de Versões */}
        <div className="space-y-3">
          <h4 className="text-[11px] font-medium uppercase tracking-widest text-content-subtle">
            Linha do tempo de versões salvas
          </h4>

          {loading ? (
            <Skeleton className="h-20" />
          ) : revisions.length === 0 ? (
            <div className="rounded-xl border border-line-subtle bg-canvas/40 p-6 text-center">
              <p className="text-xs text-content-muted">
                Nenhum snapshot historizado ainda. Crie o primeiro acima para salvar o estado
                atual do documento.
              </p>
            </div>
          ) : (
            <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
              {revisions.map((rev) => (
                <div
                  key={rev.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line-subtle bg-canvas/60 p-4"
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge tone="info" className="tnum font-mono text-[10px]">
                        v{rev.versao}
                      </Badge>
                      <span className="truncate text-sm font-semibold text-content-primary">
                        {rev.rotulo}
                      </span>
                    </div>
                    {rev.descricao && (
                      <p className="truncate text-xs text-content-muted">{rev.descricao}</p>
                    )}
                    <p className="tnum text-[10px] text-content-subtle">
                      {new Date(rev.created_at).toLocaleString('pt-BR')} — {rev.items_snapshot.length}{' '}
                      itens salvos
                    </p>
                  </div>

                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setRestoreConfirm({ versao: rev.versao, rotulo: rev.rotulo })}
                    disabled={restoringVersao === rev.versao}
                    loading={restoringVersao === rev.versao}
                    className="shrink-0"
                  >
                    {restoringVersao === rev.versao ? 'Restaurando…' : 'Restaurar esta Versão'}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>

      <ConfirmDialog
        open={restoreConfirm !== null}
        title="Restaurar versão"
        message={
          restoreConfirm
            ? `Deseja restaurar os itens do documento para a versão ${restoreConfirm.versao} ('${restoreConfirm.rotulo}')?`
            : ''
        }
        confirmLabel="Restaurar"
        onConfirm={() => {
          if (restoreConfirm) handleRestore(restoreConfirm.versao, restoreConfirm.rotulo);
          setRestoreConfirm(null);
        }}
        onCancel={() => setRestoreConfirm(null)}
      />
    </Dialog>
  );
}
