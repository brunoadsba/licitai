'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getDocument, startAnalysis, getDocumentAnalyses, getAnalysis } from '@/lib/api';
import RevisionsTimelineModal from '@/components/RevisionsTimelineModal';
import type {
  DocumentDetailResponse,
  DocumentItemResponse,
  AnalysisDetailResponse,
  CorrectionResponse,
} from '@/types';
import { CATEGORY_LABELS, SEVERITY_LABELS } from '@/types';

const AGENT_ORIGIN_CONFIG: Record<string, { label: string; icon: string; badgeClass: string }> = {
  juridico: { label: 'Agente Jurídico', icon: '⚖️', badgeClass: 'bg-purple-500/15 text-purple-300 border-purple-500/40' },
  tecnico: { label: 'Agente Técnico', icon: '🛠️', badgeClass: 'bg-amber-500/15 text-amber-300 border-amber-500/40' },
  redacao: { label: 'Agente de Redação', icon: '✍️', badgeClass: 'bg-blue-500/15 text-blue-300 border-blue-500/40' },
  estrutural: { label: 'Agente Estrutural', icon: '📐', badgeClass: 'bg-teal-500/15 text-teal-300 border-teal-500/40' },
};

export default function AnalysisPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.id as string;

  const [document, setDocument] = useState<DocumentDetailResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisDetailResponse | null>(null);
  const [selectedItem, setSelectedItem] = useState<DocumentItemResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [revisionsModalOpen, setRevisionsModalOpen] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const doc = await getDocument(documentId);
      setDocument(doc);

      if (doc.items.length > 0 && !selectedItem) {
        setSelectedItem(doc.items[0]);
      }

      // Carregar análise mais recente
      const analyses = await getDocumentAnalyses(documentId);
      if (analyses.length > 0) {
        setAnalysis(analyses[0]);
      }
    } catch {
      setError('Erro ao carregar documento.');
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Polling durante análise
  useEffect(() => {
    if (!analysis || !['pending', 'running'].includes(analysis.status)) return;

    const interval = setInterval(async () => {
      try {
        const updated = await getAnalysis(analysis.id);
        setAnalysis(updated);

        if (['completed', 'error'].includes(updated.status)) {
          clearInterval(interval);
        }
      } catch {
        // silenciar erros de polling
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [analysis?.id, analysis?.status]);

  async function handleStartAnalysis() {
    try {
      setAnalyzing(true);
      setError(null);
      const result = await startAnalysis(documentId);

      // Carregar a análise criada
      const newAnalysis = await getAnalysis(result.analysis_id);
      setAnalysis(newAnalysis);
    } catch (err: any) {
      setError(err.message || 'Erro ao iniciar análise.');
    } finally {
      setAnalyzing(false);
    }
  }

  function handleCopy(text: string, key: string) {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  }

  function getItemCorrections(itemId: string): CorrectionResponse[] {
    if (!analysis?.corrections) return [];
    return analysis.corrections.filter((c) => c.document_item_id === itemId);
  }

  function getUpdatedItemText(item: DocumentItemResponse, corrections: CorrectionResponse[]): string {
    let text = item.content;
    for (const c of corrections) {
      if (c.original_text && c.suggested_text && text.includes(c.original_text)) {
        text = text.replace(c.original_text, c.suggested_text);
      }
    }
    return text;
  }

  function getCategoryBadge(category: string) {
    const classes: Record<string, string> = {
      juridica: 'badge-juridica',
      tecnica: 'badge-tecnica',
      redacao: 'badge-redacao',
      estrutural: 'badge-estrutural',
    };
    return classes[category] || 'badge-info';
  }

  function getSeverityBadge(severity: string) {
    const classes: Record<string, string> = {
      info: 'badge-info',
      baixo: 'badge-baixo',
      medio: 'badge-medio',
      alto: 'badge-alto',
      critico: 'badge-critico',
    };
    return classes[severity] || 'badge-info';
  }

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="skeleton h-12 w-64" />
        <div className="grid grid-cols-4 gap-4">
          <div className="skeleton h-[600px]" />
          <div className="col-span-3 skeleton h-[600px]" />
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="glass-card p-12 text-center">
        <p className="text-gray-400">Documento não encontrado.</p>
        <Link href="/" className="btn-primary mt-4 inline-flex">Voltar</Link>
      </div>
    );
  }

  const progress = analysis
    ? Math.round((analysis.analyzed_items / Math.max(analysis.total_items, 1)) * 100)
    : 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
            <Link href="/" className="hover:text-gray-300 transition-colors">Painel</Link>
            <span>›</span>
            <span className="text-gray-400">Análise</span>
          </div>
          <h1 className="text-xl font-bold text-white truncate max-w-xl">
            {document.filename_original}
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            {document.total_items} itens • {document.file_type.toUpperCase()}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setRevisionsModalOpen(true)}
            className="btn-secondary"
            title="Ver e salvar histórico de edições/snapshots"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Histórico de Edições
          </button>

          {analysis?.status === 'completed' && (
            <Link
              href={`/report/${analysis.id}`}
              className="btn-secondary"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
              </svg>
              Ver Relatório
            </Link>
          )}

          {(!analysis || analysis.status === 'completed') && document.status !== 'error' && (
            <button
              onClick={handleStartAnalysis}
              disabled={analyzing}
              className="btn-primary"
            >
              {analyzing ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Iniciando...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
                  </svg>
                  {analysis ? 'Reanalisar' : 'Iniciar Análise'}
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Barra de progresso da análise */}
      {analysis && ['pending', 'running'].includes(analysis.status) && (
        <div className="glass-card p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-primary-400 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span className="text-sm text-gray-300">Analisando com IA...</span>
            </div>
            <span className="text-sm text-gray-500">
              {analysis.analyzed_items} / {analysis.total_items} itens
            </span>
          </div>
          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* Erro */}
      {error && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Layout principal: itens à esquerda, detalhes à direita */}
      <div className="grid grid-cols-12 gap-6">
        {/* Lista de itens */}
        <div className="col-span-4 space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto pr-2">
          {document.items.map((item) => {
            const corrections = getItemCorrections(item.id);
            const isActive = selectedItem?.id === item.id;
            const hasIssues = corrections.length > 0;
            const maxSeverity = corrections.reduce((max: string, c: CorrectionResponse) => {
              const order = ['info', 'baixo', 'medio', 'alto', 'critico'];
              return order.indexOf(c.severity) > order.indexOf(max) ? c.severity : max;
            }, 'info');

            return (
              <button
                key={item.id}
                onClick={() => setSelectedItem(item)}
                className={`w-full text-left p-4 rounded-xl transition-all duration-200 ${
                  isActive
                    ? 'bg-primary-500/10 border border-primary-500/30'
                    : 'glass-card-interactive'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <span className="text-xs text-primary-400 font-mono">
                      {item.item_number}
                    </span>
                    {item.title && (
                      <p className="text-sm text-gray-200 font-medium truncate mt-0.5">
                        {item.title}
                      </p>
                    )}
                    <p className="text-xs text-gray-500 mt-1">
                      {item.item_type} • pág. {item.page_number || '—'}
                    </p>
                  </div>

                  {hasIssues && (
                    <span className={`badge ${getSeverityBadge(maxSeverity)} text-[10px]`}>
                      {corrections.length}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Detalhe do item selecionado */}
        <div className="col-span-8 space-y-4">
          {selectedItem ? (
            <>
              {/* Conteúdo do item */}
              <div className="glass-card p-6">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-sm font-mono text-primary-400 font-semibold">
                    {selectedItem.item_number}
                  </span>
                  {selectedItem.title && (
                    <h3 className="text-lg font-semibold text-white">
                      {selectedItem.title}
                    </h3>
                  )}
                  <span className="badge badge-info text-[10px] ml-auto">
                    {selectedItem.item_type}
                  </span>
                </div>

                <div className="bg-surface-900/50 rounded-xl p-4 max-h-48 overflow-y-auto mb-4">
                  <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
                    {selectedItem.content}
                  </p>
                </div>

                {/* Ação de Copiar Item Inteiro Atualizado (para o SEI) */}
                {getItemCorrections(selectedItem.id).length > 0 && (
                  <div className="flex items-center justify-between pt-3 border-t border-white/[0.06]">
                    <span className="text-xs text-gray-400">
                      💡 Copie o item completo pronto para o SEI (com correções aplicadas):
                    </span>
                    <button
                      onClick={() =>
                        handleCopy(
                          getUpdatedItemText(selectedItem, getItemCorrections(selectedItem.id)),
                          `item_full_${selectedItem.id}`
                        )
                      }
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary-600/20 hover:bg-primary-600/30 text-primary-300 border border-primary-500/30 flex items-center gap-1.5 transition-all"
                    >
                      {copiedKey === `item_full_${selectedItem.id}` ? (
                        <>
                          <svg className="w-3.5 h-3.5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                          </svg>
                          Copiado!
                        </>
                      ) : (
                        <>
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.757c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                          </svg>
                          Copiar Item Inteiro para o SEI
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>

              {/* Correções do item */}
              {analysis && (
                <div className="space-y-3">
                  {getItemCorrections(selectedItem.id).length === 0 ? (
                    <div className="glass-card p-6 text-center">
                      <svg className="w-10 h-10 mx-auto text-green-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="text-green-400 font-medium text-sm">Item adequado</p>
                      <p className="text-gray-500 text-xs mt-1">
                        Nenhuma correção necessária. Não é preciso alterar este item no SEI.
                      </p>
                    </div>
                  ) : (
                    getItemCorrections(selectedItem.id).map((correction, idx) => (
                      <div key={correction.id} className="glass-card p-5 animate-slide-up" style={{ animationDelay: `${idx * 80}ms` }}>
                        {/* Header da correção */}
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-2 flex-wrap">
                            {correction.agent_origin && AGENT_ORIGIN_CONFIG[correction.agent_origin] && (
                              <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border flex items-center gap-1 ${AGENT_ORIGIN_CONFIG[correction.agent_origin].badgeClass}`}>
                                <span>{AGENT_ORIGIN_CONFIG[correction.agent_origin].icon}</span>
                                {AGENT_ORIGIN_CONFIG[correction.agent_origin].label}
                              </span>
                            )}
                            <span className={`badge ${getCategoryBadge(correction.category)}`}>
                              {CATEGORY_LABELS[correction.category] || correction.category}
                            </span>
                            <span className={`badge ${getSeverityBadge(correction.severity)}`}>
                              {SEVERITY_LABELS[correction.severity] || correction.severity}
                            </span>
                          </div>

                          {/* Botão Principal de Copiar o PARA */}
                          <button
                            onClick={() => handleCopy(correction.suggested_text, `para_${correction.id}`)}
                            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-green-500/20 hover:bg-green-500/30 text-green-300 border border-green-500/40 flex items-center gap-1.5 transition-all shadow-sm"
                            title="Copiar texto de substituição para colar no SEI"
                          >
                            {copiedKey === `para_${correction.id}` ? (
                              <>
                                <svg className="w-3.5 h-3.5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                                </svg>
                                Texto Copiado!
                              </>
                            ) : (
                              <>
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.757c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                                </svg>
                                Copiar Texto Corrigido (PARA)
                              </>
                            )}
                          </button>
                        </div>

                        {/* Problema */}
                        <p className="text-sm text-gray-300 mb-4">{correction.problem}</p>

                        {/* DE → PARA */}
                        <div className="space-y-2 mb-4">
                          <div className="diff-removed">
                            <p className="text-xs text-red-400/70 font-semibold uppercase tracking-wider mb-1">DE (original)</p>
                            <p className="text-sm text-red-300/90">{correction.original_text}</p>
                          </div>
                          <div className="diff-added relative group">
                            <div className="flex items-center justify-between mb-1">
                              <p className="text-xs text-green-400/70 font-semibold uppercase tracking-wider">PARA (sugerido)</p>
                              <button
                                onClick={() => handleCopy(correction.suggested_text, `para_sub_${correction.id}`)}
                                className="text-[11px] text-green-400/80 hover:text-green-300 underline"
                              >
                                {copiedKey === `para_sub_${correction.id}` ? 'Copiado!' : 'Copiar'}
                              </button>
                            </div>
                            <p className="text-sm text-green-300/90">{correction.suggested_text}</p>
                          </div>
                        </div>

                        {/* Justificativa e Fundamento Legal */}
                        <div className="bg-surface-900/30 rounded-lg p-3 relative">
                          <div className="flex items-center justify-between mb-1">
                            <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider">Justificativa & Fundamentação</p>
                            <button
                              onClick={() =>
                                handleCopy(
                                  `${correction.justification}${correction.legal_basis ? ` (Fundamento: ${correction.legal_basis})` : ''}`,
                                  `just_${correction.id}`
                                )
                              }
                              className="text-[11px] text-primary-400/80 hover:text-primary-300 underline"
                            >
                              {copiedKey === `just_${correction.id}` ? 'Copiado!' : 'Copiar Justificativa'}
                            </button>
                          </div>
                          <p className="text-sm text-gray-400">{correction.justification}</p>
                          {correction.legal_basis && (
                            <p className="text-xs text-primary-400 mt-2 font-mono">
                              📋 {correction.legal_basis}
                            </p>
                          )}
                        </div>

                        {/* Risco */}
                        <div className="mt-3 flex items-start gap-2">
                          <svg className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                          </svg>
                          <p className="text-xs text-yellow-400/70">{correction.risk}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="glass-card p-12 text-center">
              <p className="text-gray-500">Selecione um item para ver os detalhes.</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal de Histórico e Versionamento de Edições (Single-User) */}
      <RevisionsTimelineModal
        documentId={documentId}
        isOpen={revisionsModalOpen}
        onClose={() => setRevisionsModalOpen(false)}
        onRestored={() => loadData()}
      />
    </div>
  );
}
