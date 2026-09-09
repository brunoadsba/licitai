'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  listComparacoes,
  listMoldes,
  listDocuments,
  listFornecedores,
  startComparacao,
  enviarFeedback,
  extractErrorMessage,
} from '@/lib/api';
import { formatFeedbackMessage } from '@/components/comparacao/formatFeedbackMessage';
import { useFornecedorPanelState } from '@/components/comparacao/useFornecedorPanelState';
import type { DocumentResponse, Molde } from '@/types';

export interface ComparacaoRow {
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

export function useComparacaoPage() {
  const [comparacoes, setComparacoes] = useState<ComparacaoRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trs, setTrs] = useState<DocumentResponse[]>([]);
  const [propostas, setPropostas] = useState<DocumentResponse[]>([]);
  const [moldes, setMoldes] = useState<Molde[]>([]);
  const [trId, setTrId] = useState('');
  const [moldeId, setMoldeId] = useState('');
  const [propostaIds, setPropostaIds] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [sendingFeedbackId, setSendingFeedbackId] = useState<string | null>(null);
  const [feedbackEnviadosIds, setFeedbackEnviadosIds] = useState<string[]>([]);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const fornecedor = useFornecedorPanelState({ setError, setPropostas });

  const loadAll = useCallback(async () => {
    try {
      setLoading(true);
      const [cmp, docsData, moldesData, fornecedoresData] = await Promise.all([
        listComparacoes(),
        listDocuments(),
        listMoldes(),
        listFornecedores(),
      ]);
      setComparacoes(cmp.comparacoes);
      setTrs(docsData.documents.filter((d) => d.document_type === 'tr'));
      setPropostas(docsData.documents.filter((d) => d.document_type === 'proposta'));
      setMoldes(moldesData.moldes);
      fornecedor.setFornecedores(fornecedoresData.fornecedores);
    } catch {
      setError('Não foi possível carregar a auditoria. Tente atualizar a página.');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  function toggleProposta(id: string) {
    setPropostaIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
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

  async function handleFeedback(id: string) {
    try {
      setSendingFeedbackId(id);
      setError(null);
      setFeedbackMsg(null);
      const result = await enviarFeedback(id);
      setFeedbackMsg(formatFeedbackMessage(result));
      setFeedbackEnviadosIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao enviar pendências.'));
    } finally {
      setSendingFeedbackId(null);
    }
  }

  return {
    comparacoes,
    loading,
    error,
    trs,
    propostas,
    moldes,
    propostaIds,
    submitting,
    sendingFeedbackId,
    feedbackEnviadosIds,
    feedbackMsg,
    fornecedores: fornecedor.fornecedores,
    novoFornecedor: fornecedor.novoFornecedor,
    novoFornecedorCnpj: fornecedor.novoFornecedorCnpj,
    novoFornecedorEmail: fornecedor.novoFornecedorEmail,
    editandoFornecedorId: fornecedor.editandoFornecedorId,
    propostaFile: fornecedor.propostaFile,
    propostaFornecedorId: fornecedor.propostaFornecedorId,
    uploading: fornecedor.uploading,
    confirmDeleteId: fornecedor.confirmDeleteId,
    setTrId,
    setMoldeId,
    setNovoFornecedor: fornecedor.setNovoFornecedor,
    setNovoFornecedorCnpj: fornecedor.setNovoFornecedorCnpj,
    setNovoFornecedorEmail: fornecedor.setNovoFornecedorEmail,
    setPropostaFornecedorId: fornecedor.setPropostaFornecedorId,
    setPropostaFile: fornecedor.setPropostaFile,
    setConfirmDeleteId: fornecedor.setConfirmDeleteId,
    toggleProposta,
    handleStart,
    handleCadastrarFornecedor: fornecedor.handleCadastrarFornecedor,
    handleEditarFornecedor: fornecedor.handleEditarFornecedor,
    clearFornecedorForm: fornecedor.clearFornecedorForm,
    handleExcluirFornecedor: fornecedor.handleExcluirFornecedor,
    handleFeedback,
    handleUploadProposta: fornecedor.handleUploadProposta,
  };
}
