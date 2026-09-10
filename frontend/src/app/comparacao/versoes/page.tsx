'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRightLeft, FileText } from 'lucide-react';
import { listDocuments, diffDocuments, extractErrorMessage } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { Badge } from '@/components/ui/Badge';
import type { Tone } from '@/components/ui/Badge';
import type { DiffItemResponse, DocumentResponse } from '@/types';

interface DiffResult {
  total: number;
  resumo?: { alterados?: number; adicionados?: number; removidos?: number };
  itens: DiffItemResponse[];
}

function getStatusTone(status: string): Tone {
  switch (status) {
    case 'inalterado':
      return 'neutral';
    case 'alterado':
      return 'medium';
    case 'adicionado':
      return 'low';
    case 'removido':
      return 'critical';
    default:
      return 'neutral';
  }
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
      {/* Cabeçalho */}
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight text-content-primary">
          <ArrowRightLeft className="h-6 w-6 text-accent-400" aria-hidden />
          Comparador de Versões de TR
        </h1>
        <p className="mt-1 text-sm text-content-muted">
          Alinhamento inteligente item por item para identificar acréscimos, exclusões e
          alterações de texto entre duas versões do Termo de Referência.
        </p>
      </div>

      {error && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Card de Seleção */}
      <div className="glass-card space-y-4 p-5 sm:p-6">
        <h2 className="text-[11px] font-medium uppercase tracking-widest text-content-subtle">
          Selecione as versões para comparação
        </h2>

        {loading ? (
          <Skeleton className="h-12" />
        ) : documents.length < 2 ? (
          <EmptyState
            icon={FileText}
            title="Poucos TRs para comparar"
            description="Cadastre pelo menos dois Termos de Referência no Painel para comparar versões."
            action={
              <Link href="/upload">
                <Button>Enviar Documento</Button>
              </Link>
            }
            className="py-10"
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label
                htmlFor="versao-antiga"
                className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-content-muted"
              >
                <FileText className="h-3.5 w-3.5 text-content-subtle" aria-hidden />
                Versão Original (Antiga)
              </label>
              <select
                id="versao-antiga"
                value={docAntigoId}
                onChange={(e) => setDocAntigoId(e.target.value)}
                className="input-field tnum w-full text-sm"
              >
                {documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.filename_original} ({d.total_items} itens) —{' '}
                    {new Date(d.created_at).toLocaleDateString('pt-BR')}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="versao-nova"
                className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-content-muted"
              >
                <FileText className="h-3.5 w-3.5 text-accent-400" aria-hidden />
                Nova Versão (Revisada)
              </label>
              <select
                id="versao-nova"
                value={docNovoId}
                onChange={(e) => setDocNovoId(e.target.value)}
                className="input-field tnum w-full text-sm"
              >
                {documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.filename_original} ({d.total_items} itens) —{' '}
                    {new Date(d.created_at).toLocaleDateString('pt-BR')}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        <div className="pt-2">
          <Button
            onClick={handleCompare}
            loading={diffing}
            disabled={diffing || documents.length < 2 || docAntigoId === docNovoId}
          >
            {diffing ? 'Comparando…' : 'Comparar Versões'}
          </Button>
        </div>
      </div>

      {/* Resultado do Diff */}
      {diffResult && (
        <div className="space-y-6">
          {/* Resumo da comparação */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="glass-card p-4 text-center">
              <p className="text-xs text-content-muted">Total de Itens</p>
              <p className="tnum mt-1 text-2xl font-semibold tracking-tight text-content-primary">
                {diffResult.total}
              </p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-xs font-medium text-amber-400">Alterados</p>
              <p className="tnum mt-1 text-2xl font-semibold tracking-tight text-amber-400">
                {diffResult.resumo?.alterados || 0}
              </p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-xs font-medium text-green-400">Adicionados</p>
              <p className="tnum mt-1 text-2xl font-semibold tracking-tight text-green-400">
                {diffResult.resumo?.adicionados || 0}
              </p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-xs font-medium text-red-400">Removidos</p>
              <p className="tnum mt-1 text-2xl font-semibold tracking-tight text-red-400">
                {diffResult.resumo?.removidos || 0}
              </p>
            </div>
          </div>

          {docNovoId && docAntigoId && (
            <div className="glass-card flex flex-wrap items-center justify-between gap-3 border-accent-500/20 p-4">
              <div>
                <p className="text-sm font-medium text-content-primary">Próximo passo</p>
                <p className="text-xs text-content-muted">
                  Analise a versão nova e revise só os achados prioritários antes de colar no SEI.
                </p>
              </div>
              <Link
                href={`/analysis/${docNovoId}?diffFrom=${encodeURIComponent(docAntigoId)}`}
              >
                <Button size="sm">Revisar versão nova</Button>
              </Link>
            </div>
          )}

          {/* Lista de Itens comparados */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold tracking-tight text-content-primary">
              Detalhamento das Alterações
            </h2>

            {diffResult.itens.map((item) => (
              <div key={item.item_number} className="glass-card space-y-3 p-5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <span className="tnum font-mono text-sm font-semibold text-accent-400">
                      Item {item.item_number}
                    </span>
                    {item.titulo && (
                      <h3 className="max-w-md truncate text-sm font-semibold text-content-primary">
                        {item.titulo}
                      </h3>
                    )}
                  </div>
                  <Badge tone={getStatusTone(item.status)} className="uppercase text-[10px]">
                    {item.status}
                  </Badge>
                </div>

                {/* Exibição do diff textual */}
                {item.status === 'alterado' && (
                  <div className="space-y-2 pt-2">
                    <div className="diff-removed">
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-red-400/70">
                        Versão Anterior
                      </p>
                      <p className="whitespace-pre-wrap text-sm text-red-300/90">
                        {item.conteudo_antes}
                      </p>
                    </div>
                    <div className="diff-added">
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-green-400/70">
                        Nova Versão
                      </p>
                      <p className="whitespace-pre-wrap text-sm text-green-300/90">
                        {item.conteudo_depois}
                      </p>
                    </div>
                  </div>
                )}

                {item.status === 'adicionado' && (
                  <div className="diff-added">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-green-400/70">
                      Novo Item Adicionado
                    </p>
                    <p className="whitespace-pre-wrap text-sm text-green-300/90">
                      {item.conteudo_depois}
                    </p>
                  </div>
                )}

                {item.status === 'removido' && (
                  <div className="diff-removed">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-red-400/70">
                      Item Excluído
                    </p>
                    <p className="whitespace-pre-wrap text-sm text-red-300/90">
                      {item.conteudo_antes}
                    </p>
                  </div>
                )}

                {item.status === 'inalterado' && (
                  <p className="text-xs italic text-content-subtle">
                    Item idêntico em ambas as versões.
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
