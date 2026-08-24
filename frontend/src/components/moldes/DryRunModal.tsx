'use client';

import { useEffect, useState } from 'react';
import { listDocuments, validateMoldeDryRun , extractErrorMessage } from '@/lib/api';
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
  const [dryRunResult, setDryRunResult] = useState<any | null>(null);

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
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card max-w-2xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <span>🔑</span> Validar Molde contra TR (Dry-Run)
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Molde: <span className="text-primary-300 font-semibold">{molde.nome}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-lg font-bold"
          >
            ✕
          </button>
        </div>

        <div className="space-y-2">
          <label className="block text-xs font-semibold text-gray-300">
            Selecione o Termo de Referência para teste:
          </label>
          {docsList.length === 0 ? (
            <p className="text-xs text-amber-400">
              Nenhum Termo de Referência encontrado. Envie um documento TR na tela de Upload.
            </p>
          ) : (
            <div className="flex items-center gap-3">
              <select
                value={selectedDocId}
                onChange={(e) => setSelectedDocId(e.target.value)}
                className="input-field flex-1 text-sm bg-surface-900"
              >
                {docsList.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.filename_original} ({doc.total_items} itens)
                  </option>
                ))}
              </select>
              <button
                onClick={executeDryRun}
                disabled={dryRunLoading || !selectedDocId}
                className="btn-primary shrink-0"
              >
                {dryRunLoading ? 'Executando...' : 'Testar Extração'}
              </button>
            </div>
          )}
        </div>

        {dryRunResult && (
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between bg-surface-900/60 p-3 rounded-lg border border-white/10">
              <div>
                <span className="text-xs text-gray-400">Total de regras: </span>
                <span className="text-xs font-bold text-white">{dryRunResult.total_regras}</span>
              </div>
              <div>
                <span className="text-xs text-gray-400">Correspondências no TR: </span>
                <span className="text-xs font-bold text-green-400">{dryRunResult.regras_encontradas} / {dryRunResult.total_regras}</span>
              </div>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto">
              {dryRunResult.resultados.map((r: DryRunResultado) => (
                <div
                  key={r.regra_id}
                  className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
                    r.encontrado
                      ? 'bg-green-500/10 border-green-500/30 text-green-300'
                      : 'bg-surface-900/40 border-white/5 text-gray-400'
                  }`}
                >
                  <div>
                    <span className="font-semibold text-gray-200">{r.rotulo}</span>
                    <span className="text-[10px] text-gray-500 ml-2 font-mono">({r.tipo})</span>
                    {r.ancora && (
                      <p className="text-[11px] text-gray-400 mt-0.5">Âncora: &quot;{r.ancora}&quot;</p>
                    )}
                  </div>
                  <div className="text-right">
                    {r.encontrado ? (
                      <span className="font-bold text-green-300 bg-green-500/20 px-2 py-0.5 rounded border border-green-500/30">
                        {r.valor_extraido}
                      </span>
                    ) : (
                      <span className="text-gray-500 italic">Não encontrado</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
