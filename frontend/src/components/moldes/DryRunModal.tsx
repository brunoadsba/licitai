'use client';

import { useEffect, useState } from 'react';
import { FlaskConical, X } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { listDocuments, validateMoldeDryRun, extractErrorMessage } from '@/lib/api';
import { Molde, DocumentResponse, DryRunResultado } from '@/types';

interface DryRunModalProps {
  molde: Molde;
  onClose: () => void;
  onError: (msg: string) => void;
}

export default function DryRunModal({ molde, onClose, onError }: DryRunModalProps) {
  const [docsList, setDocsList] = useState<DocumentResponse[]>([]);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [dryRunLoading, setDryRunLoading] = useState(false);
  const [dryRunResult, setDryRunResult] = useState<{
    total_regras: number;
    regras_encontradas: number;
    resultados: DryRunResultado[];
  } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setDryRunResult(null);
        const res = await listDocuments();
        const trDocs = res.documents.filter((d) => d.document_type === 'tr');
        setDocsList(trDocs);
        if (trDocs.length > 0) {
          setSelectedDocId(trDocs[0].id);
        }
      } catch {
        onError('Erro ao carregar documentos para validação.');
      }
    })();
  }, [molde.id, onError]);

  async function executeDryRun() {
    if (!selectedDocId) return;
    try {
      setDryRunLoading(true);
      const res = await validateMoldeDryRun(molde.id, selectedDocId);
      setDryRunResult(res);
    } catch (err) {
      onError(extractErrorMessage(err, 'Erro ao executar validação dry-run.'));
    } finally {
      setDryRunLoading(false);
    }
  }

  return (
    <Dialog open onOpenChange={(next) => (!next ? onClose() : undefined)}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-amber-300" aria-hidden />
            Validar Molde contra TR (Dry-Run)
          </DialogTitle>
          <DialogDescription>
            Molde: <span className="font-semibold text-accent-400">{molde.nome}</span> — testa as
            regras contra um TR real sem salvar nada.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <label htmlFor="dryrun-doc" className="block text-xs font-medium text-content-secondary">
            Selecione o Termo de Referência para teste:
          </label>
          {docsList.length === 0 ? (
            <p className="text-xs text-amber-400">
              Nenhum Termo de Referência encontrado. Envie um documento TR na tela de Upload.
            </p>
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <select
                id="dryrun-doc"
                value={selectedDocId}
                onChange={(e) => setSelectedDocId(e.target.value)}
                className="input-field tnum flex-1 text-sm"
              >
                {docsList.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.filename_original} ({doc.total_items} itens)
                  </option>
                ))}
              </select>
              <Button
                onClick={executeDryRun}
                disabled={dryRunLoading || !selectedDocId}
                loading={dryRunLoading}
                className="shrink-0"
              >
                {dryRunLoading ? 'Executando…' : 'Testar Extração'}
              </Button>
            </div>
          )}
        </div>

        {dryRunResult && (
          <div className="space-y-3 pt-2">
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line-strong bg-canvas/60 p-3">
              <div className="text-xs text-content-muted">
                Total de regras:{' '}
                <span className="tnum font-semibold text-content-primary">
                  {dryRunResult.total_regras}
                </span>
              </div>
              <div className="text-xs text-content-muted">
                Correspondências no TR:{' '}
                <span className="tnum font-semibold text-green-400">
                  {dryRunResult.regras_encontradas} / {dryRunResult.total_regras}
                </span>
              </div>
            </div>

            <div className="max-h-60 space-y-2 overflow-y-auto pr-1">
              {dryRunResult.resultados.map((r) => (
                <div
                  key={r.regra_id}
                  className={`flex items-center justify-between rounded-lg border p-3 text-xs ${
                    r.encontrado
                      ? 'border-green-500/30 bg-green-500/10 text-green-300'
                      : 'border-line-subtle bg-canvas/40 text-content-muted'
                  }`}
                >
                  <div>
                    <span className="font-semibold text-content-primary">{r.rotulo}</span>
                    <span className="tnum ml-2 font-mono text-[10px] text-content-subtle">
                      ({r.tipo})
                    </span>
                    {r.ancora && (
                      <p className="mt-0.5 text-[11px] text-content-muted">
                        Âncora: &quot;{r.ancora}&quot;
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    {r.encontrado ? (
                      <span className="tnum rounded border border-green-500/30 bg-green-500/20 px-2 py-0.5 font-semibold text-green-300">
                        {r.valor_extraido}
                      </span>
                    ) : (
                      <span className="italic text-content-subtle">Não encontrado</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
