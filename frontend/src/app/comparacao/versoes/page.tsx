'use client';

import { useEffect, useState } from 'react';
import { ArrowRightLeft } from 'lucide-react';
import { listDocuments, diffDocuments, extractErrorMessage } from '@/lib/api';
import VersoesSelector from '@/components/comparacao/VersoesSelector';
import VersoesDiffResult from '@/components/comparacao/VersoesDiffResult';
import type { DiffItemResponse, DocumentResponse } from '@/types';

interface DiffResult {
  total: number;
  resumo?: { alterados?: number; adicionados?: number; removidos?: number };
  itens: DiffItemResponse[];
}

export default function DiffVersoesPage() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [docAntigoId, setDocAntigoId] = useState<string>('');
  const [docNovoId, setDocNovoId] = useState<string>('');
  const [diffing, setDiffing] = useState(false);
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await listDocuments();
        const trs = res.documents.filter((d) => d.document_type === 'tr');
        setDocuments(trs);
        setError(null);
        if (trs.length >= 2) {
          setDocAntigoId(trs[1].id);
          setDocNovoId(trs[0].id);
        } else if (trs.length === 1) {
          setDocAntigoId(trs[0].id);
          setDocNovoId(trs[0].id);
        }
      } catch {
        setError('Não foi possível carregar a lista de Termos de Referência.');
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
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao comparar versões do TR.'));
    } finally {
      setDiffing(false);
    }
  }

  return (
    <div className="animate-fade-in mx-auto max-w-6xl space-y-8">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight text-content-primary">
          <ArrowRightLeft className="h-6 w-6 text-accent-400" aria-hidden />
          Comparador de Versões de TR
        </h1>
        <p className="mt-1 text-sm text-content-muted">
          Alinhamento inteligente item por item para identificar acréscimos, exclusões e alterações de texto entre duas versões do Termo de Referência.
        </p>
      </header>

      {error && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      <VersoesSelector
        documents={documents}
        loading={loading}
        docAntigoId={docAntigoId}
        docNovoId={docNovoId}
        diffing={diffing}
        onChangeAntigo={setDocAntigoId}
        onChangeNovo={setDocNovoId}
        onCompare={handleCompare}
      />

      {diffResult && <VersoesDiffResult diffResult={diffResult} docAntigoId={docAntigoId} docNovoId={docNovoId} />}
    </div>
  );
}
