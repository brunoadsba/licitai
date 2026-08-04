'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  listComparacoes,
  listFornecedores,
  listMoldes,
  listDocuments,
  createFornecedor,
  updateFornecedor,
  deleteFornecedor,
  createMolde,
  startComparacao,
  enviarFeedback,
  uploadDocument,
} from '@/lib/api';
import {
  COMPARACAO_STATUS_LABELS,
} from '@/types';

interface Comparacao {
  id: string;
  tr_document_id: string;
  molde_id: string;
  status: string;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  total_resultados: number;
  fornecedores: { id: string; nome: string }[];
}

export default function ComparacaoPage() {
  const [comparacoes, setComparacoes] = useState<Comparacao[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dados para criar comparação
  const [trs, setTrs] = useState<any[]>([]);
  const [propostas, setPropostas] = useState<any[]>([]);
  const [moldes, setMoldes] = useState<any[]>([]);
  const [fornecedores, setFornecedores] = useState<any[]>([]);

  const [trId, setTrId] = useState('');
  const [moldeId, setMoldeId] = useState('');
  const [propostaIds, setPropostaIds] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Upload de proposta
  const [novoFornecedor, setNovoFornecedor] = useState('');
  const [novoFornecedorCnpj, setNovoFornecedorCnpj] = useState('');
  const [novoFornecedorEmail, setNovoFornecedorEmail] = useState('');
  const [editandoFornecedorId, setEditandoFornecedorId] = useState<string | null>(null);
  const [propostaFile, setPropostaFile] = useState<File | null>(null);
  const [propostaFornecedorId, setPropostaFornecedorId] = useState('');
  const [uploading, setUploading] = useState(false);

  // Feedback de pendências por e-mail (RF04)
  const [sendingFeedbackId, setSendingFeedbackId] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    try {
      setLoading(true);
      const [cmp, trsData, propData, moldesData, fornecedoresData] =
        await Promise.all([
          listComparacoes(),
          listDocuments(),
          listDocuments(),
          listMoldes(),
          listFornecedores(),
        ]);
      setComparacoes(cmp.comparacoes);
      setTrs(trsData.documents.filter((d: any) => d.document_type === 'tr'));
      setPropostas(propData.documents.filter((d: any) => d.document_type === 'proposta'));
      setMoldes(moldesData.moldes);
      setFornecedores(fornecedoresData.fornecedores);
    } catch {
      setError('Erro ao carregar dados. Verifique se o backend está rodando.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  function toggleProposta(id: string) {
    setPropostaIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  }

  async function handleStart() {
    if (!trId || !moldeId || propostaIds.length === 0) {
      setError('Selecione o TR, o molde e ao menos uma proposta.');
      return;
    }
    try {
      setSubmitting(true);
      setError(null);
      const result = await startComparacao({
        tr_document_id: trId,
        molde_id: moldeId,
        propostas_ids: propostaIds,
      });
      setPropostaIds([]);
      await loadAll();
    } catch (err: any) {
      setError(err.message || 'Erro ao iniciar comparação.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCadastrarFornecedor() {
    if (!novoFornecedor.trim()) return;
    const dados = {
      nome: novoFornecedor.trim(),
      cnpj: novoFornecedorCnpj.trim() || undefined,
      email: novoFornecedorEmail.trim() || undefined,
    };
    try {
      if (editandoFornecedorId) {
        await updateFornecedor(editandoFornecedorId, dados);
      } else {
        await createFornecedor(dados);
      }
      setNovoFornecedor('');
      setNovoFornecedorCnpj('');
      setNovoFornecedorEmail('');
      setEditandoFornecedorId(null);
      const data = await listFornecedores();
      setFornecedores(data.fornecedores);
    } catch (err: any) {
      setError(err.message || 'Erro ao salvar fornecedor.');
    }
  }

  function handleEditarFornecedor(f: any) {
    setEditandoFornecedorId(f.id);
    setNovoFornecedor(f.nome);
    setNovoFornecedorCnpj(f.cnpj || '');
    setNovoFornecedorEmail(f.email || '');
  }

  async function handleExcluirFornecedor(id: string) {
    if (!window.confirm('Excluir este fornecedor?')) return;
    try {
      await deleteFornecedor(id);
      if (editandoFornecedorId === id) {
        setEditandoFornecedorId(null);
        setNovoFornecedor('');
        setNovoFornecedorCnpj('');
        setNovoFornecedorEmail('');
      }
      const data = await listFornecedores();
      setFornecedores(data.fornecedores);
    } catch (err: any) {
      setError(err.message || 'Erro ao excluir fornecedor.');
    }
  }

  async function handleFeedback(id: string) {
    try {
      setSendingFeedbackId(id);
      setError(null);
      setFeedbackMsg(null);
      const result = await enviarFeedback(id);
      let msg = `Pendências enviadas: ${result.enviados} e-mail(s).`;
      if (result.falhas.length > 0) {
        msg += ` Falhas: ${result.falhas.map((f) => f.nome).join(', ')}.`;
      }
      if (result.fornecedores_sem_pendencias.length > 0) {
        msg += ` Sem pendências: ${result.fornecedores_sem_pendencias.join(', ')}.`;
      }
      if (result.fornecedores_sem_email.length > 0) {
        msg += ` Sem e-mail cadastrado: ${result.fornecedores_sem_email.join(', ')}.`;
      }
      setFeedbackMsg(msg);
    } catch (err: any) {
      setError(err.message || 'Erro ao enviar pendências.');
    } finally {
      setSendingFeedbackId(null);
    }
  }

  async function handleUploadProposta() {
    if (!propostaFile || !propostaFornecedorId) {
      setError('Selecione o arquivo e o fornecedor da proposta.');
      return;
    }
    try {
      setUploading(true);
      setError(null);
      await uploadDocument(propostaFile, {
        documentType: 'proposta',
        fornecedorId: propostaFornecedorId,
      });
      setPropostaFile(null);
      setPropostaFornecedorId('');
      const data = await listDocuments();
      setPropostas(data.documents.filter((d: any) => d.document_type === 'proposta'));
    } catch (err: any) {
      setError(err.message || 'Erro ao enviar proposta.');
    } finally {
      setUploading(false);
    }
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

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Auditoria TR × Propostas</h1>
          <p className="text-gray-400 mt-1 text-sm">
            Compare as propostas dos fornecedores com o Termo de Referência
          </p>
        </div>
      </div>

      {error && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {feedbackMsg && (
        <div className="glass-card border-primary-500/30 p-4">
          <p className="text-sm text-gray-200">{feedbackMsg}</p>
        </div>
      )}

      {/* Seção de criação */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Nova Comparação</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Seleção TR e molde */}
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
                Termo de Referência
              </label>
              <select
                value={trId}
                onChange={(e) => setTrId(e.target.value)}
                className="input-field w-full"
              >
                <option value="">Selecione o TR...</option>
                {trs.map((tr) => (
                  <option key={tr.id} value={tr.id}>
                    {tr.filename_original}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
                Molde de Regras
              </label>
              <select
                value={moldeId}
                onChange={(e) => setMoldeId(e.target.value)}
                className="input-field w-full"
              >
                <option value="">Selecione o molde...</option>
                {moldes.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nome}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
                Propostas ({propostaIds.length} selecionada(s))
              </label>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {propostas.length === 0 ? (
                  <p className="text-sm text-gray-500">
                    Nenhuma proposta cadastrada. Envie uma abaixo.
                  </p>
                ) : (
                  propostas.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => toggleProposta(p.id)}
                      className={`w-full text-left p-3 rounded-xl border transition-all ${
                        propostaIds.includes(p.id)
                          ? 'bg-primary-500/10 border-primary-500/40'
                          : 'glass-card-interactive'
                      }`}
                    >
                      <p className="text-sm text-gray-200 font-medium truncate">
                        {p.filename_original}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {p.total_items} itens
                      </p>
                    </button>
                  ))
                )}
              </div>
            </div>

            <button
              onClick={handleStart}
              disabled={submitting}
              className="btn-primary w-full"
            >
              {submitting ? 'Iniciando...' : 'Iniciar Comparação'}
            </button>
          </div>

          {/* Cadastro de fornecedor e upload de proposta */}
          <div className="space-y-4">
            <div className="glass-card p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">
                {editandoFornecedorId ? 'Editar Fornecedor' : 'Cadastrar Fornecedor'}
              </h3>
              <div className="space-y-2">
                <input
                  value={novoFornecedor}
                  onChange={(e) => setNovoFornecedor(e.target.value)}
                  placeholder="Nome do fornecedor"
                  className="input-field w-full"
                />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <input
                    value={novoFornecedorCnpj}
                    onChange={(e) => setNovoFornecedorCnpj(e.target.value)}
                    placeholder="CNPJ"
                    className="input-field w-full"
                  />
                  <input
                    value={novoFornecedorEmail}
                    onChange={(e) => setNovoFornecedorEmail(e.target.value)}
                    placeholder="E-mail"
                    type="email"
                    className="input-field w-full"
                  />
                </div>
                <div className="flex gap-2">
                  <button onClick={handleCadastrarFornecedor} className="btn-secondary flex-1">
                    {editandoFornecedorId ? 'Salvar' : 'Cadastrar'}
                  </button>
                  {editandoFornecedorId && (
                    <button
                      onClick={() => {
                        setEditandoFornecedorId(null);
                        setNovoFornecedor('');
                        setNovoFornecedorCnpj('');
                        setNovoFornecedorEmail('');
                      }}
                      className="btn-secondary"
                    >
                      Cancelar
                    </button>
                  )}
                </div>
              </div>
              {fornecedores.length > 0 && (
                <div className="mt-3 space-y-1.5">
                  {fornecedores.map((f) => (
                    <div
                      key={f.id}
                      className="flex items-center justify-between gap-2 text-xs"
                    >
                      <span className="badge badge-info text-[10px] truncate flex-1">
                        {f.nome}
                        {f.email ? ` • ${f.email}` : ''}
                      </span>
                      <div className="flex gap-1 shrink-0">
                        <button
                          onClick={() => handleEditarFornecedor(f)}
                          className="btn-secondary text-[10px] px-2 py-1"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => handleExcluirFornecedor(f.id)}
                          className="btn-secondary text-[10px] px-2 py-1 text-red-400"
                        >
                          Excluir
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="glass-card p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">
                Enviar Proposta
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
                    Fornecedor
                  </label>
                  <select
                    value={propostaFornecedorId}
                    onChange={(e) => setPropostaFornecedorId(e.target.value)}
                    className="input-field w-full"
                  >
                    <option value="">Selecione o fornecedor...</option>
                    {fornecedores.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.nome}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <label className="btn-secondary cursor-pointer flex-1 text-center">
                    {propostaFile ? propostaFile.name : 'Selecionar arquivo'}
                    <input
                      type="file"
                      accept=".pdf,.docx"
                      className="hidden"
                      onChange={(e) => setPropostaFile(e.target.files?.[0] || null)}
                    />
                  </label>
                  <button
                    onClick={handleUploadProposta}
                    disabled={!propostaFile || uploading}
                    className="btn-primary"
                  >
                    {uploading ? 'Enviando...' : 'Enviar'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Listagem de comparações */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Comparações Realizadas</h2>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-20" />
            ))}
          </div>
        ) : comparacoes.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <p className="text-gray-500">Nenhuma comparação realizada ainda.</p>
          </div>
        ) : (
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
                        onClick={() => handleFeedback(cmp.id)}
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
        )}
      </div>
    </div>
  );
}
