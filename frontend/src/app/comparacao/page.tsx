'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  listComparacoes,
  listFornecedores,
  listMoldes,
  listDocuments,
  createFornecedor,
  updateFornecedor,
  deleteFornecedor,
  startComparacao,
  enviarFeedback,
  uploadDocument,
  extractErrorMessage,
} from '@/lib/api';
import type { DocumentResponse, Fornecedor, Molde } from '@/types';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import NovaComparacaoForm from '@/components/comparacao/NovaComparacaoForm';
import FornecedorPanel from '@/components/comparacao/FornecedorPanel';
import ComparacaoList from '@/components/comparacao/ComparacaoList';

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
  const [trs, setTrs] = useState<DocumentResponse[]>([]);
  const [propostas, setPropostas] = useState<DocumentResponse[]>([]);
  const [moldes, setMoldes] = useState<Molde[]>([]);
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);

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
  const [feedbackEnviadosIds, setFeedbackEnviadosIds] = useState<string[]>([]);
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
      setTrs(trsData.documents.filter((d) => d.document_type === 'tr'));
      setPropostas(propData.documents.filter((d) => d.document_type === 'proposta'));
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
      await startComparacao({
        tr_document_id: trId,
        molde_id: moldeId,
        propostas_ids: propostaIds,
      });
      setPropostaIds([]);
      await loadAll();
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao iniciar comparação.'));
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
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao salvar fornecedor.'));
    }
  }

  function handleEditarFornecedor(f: Fornecedor) {
    setEditandoFornecedorId(f.id);
    setNovoFornecedor(f.nome);
    setNovoFornecedorCnpj(f.cnpj || '');
    setNovoFornecedorEmail(f.email || '');
  }

  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  async function handleExcluirFornecedor(id: string) {
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
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao excluir fornecedor.'));
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
      setFeedbackEnviadosIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao enviar pendências.'));
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
      setPropostas(data.documents.filter((d) => d.document_type === 'proposta'));
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao enviar proposta.'));
    } finally {
      setUploading(false);
    }
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
          <NovaComparacaoForm
            trs={trs}
            moldes={moldes}
            propostas={propostas}
            propostaIds={propostaIds}
            submitting={submitting}
            onToggleProposta={toggleProposta}
            onStart={handleStart}
            setTrId={setTrId}
            setMoldeId={setMoldeId}
          />

          <FornecedorPanel
            fornecedores={fornecedores}
            editandoId={editandoFornecedorId}
            nome={novoFornecedor}
            cnpj={novoFornecedorCnpj}
            email={novoFornecedorEmail}
            propostaFornecedorId={propostaFornecedorId}
            propostaFile={propostaFile}
            uploading={uploading}
            setNome={setNovoFornecedor}
            setCnpj={setNovoFornecedorCnpj}
            setEmail={setNovoFornecedorEmail}
            setPropostaFornecedorId={setPropostaFornecedorId}
            setPropostaFile={setPropostaFile}
            onSalvar={handleCadastrarFornecedor}
            onCancelarEdicao={() => {
              setEditandoFornecedorId(null);
              setNovoFornecedor('');
              setNovoFornecedorCnpj('');
              setNovoFornecedorEmail('');
            }}
            onEditar={handleEditarFornecedor}
            onExcluir={(id) => setConfirmDeleteId(id)}
            onUpload={handleUploadProposta}
          />
        </div>
      </div>

      {/* Listagem de comparações */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Comparações Realizadas</h2>
        <ComparacaoList
          comparacoes={comparacoes}
          loading={loading}
          sendingFeedbackId={sendingFeedbackId}
          feedbackEnviadosIds={feedbackEnviadosIds}
          onFeedback={handleFeedback}
        />
      </div>

      <ConfirmDialog
        open={confirmDeleteId !== null}
        title="Excluir fornecedor"
        message="Excluir este fornecedor? Esta ação não pode ser desfeita."
        confirmLabel="Excluir"
        danger
        onConfirm={() => {
          if (confirmDeleteId) handleExcluirFornecedor(confirmDeleteId);
          setConfirmDeleteId(null);
        }}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </div>
  );
}
