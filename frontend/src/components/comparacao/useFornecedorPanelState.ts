'use client';

import { useState } from 'react';
import {
  createFornecedor,
  updateFornecedor,
  deleteFornecedor,
  listFornecedores,
  listDocuments,
  uploadDocument,
  extractErrorMessage,
} from '@/lib/api';
import type { DocumentResponse, Fornecedor } from '@/types';

export function useFornecedorPanelState(options: {
  setError: (msg: string | null) => void;
  setPropostas: (docs: DocumentResponse[]) => void;
}) {
  const { setError, setPropostas } = options;
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [novoFornecedor, setNovoFornecedor] = useState('');
  const [novoFornecedorCnpj, setNovoFornecedorCnpj] = useState('');
  const [novoFornecedorEmail, setNovoFornecedorEmail] = useState('');
  const [editandoFornecedorId, setEditandoFornecedorId] = useState<string | null>(null);
  const [propostaFile, setPropostaFile] = useState<File | null>(null);
  const [propostaFornecedorId, setPropostaFornecedorId] = useState('');
  const [uploading, setUploading] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  function clearFornecedorForm() {
    setEditandoFornecedorId(null);
    setNovoFornecedor('');
    setNovoFornecedorCnpj('');
    setNovoFornecedorEmail('');
  }

  function handleEditarFornecedor(f: Fornecedor) {
    setEditandoFornecedorId(f.id);
    setNovoFornecedor(f.nome);
    setNovoFornecedorCnpj(f.cnpj || '');
    setNovoFornecedorEmail(f.email || '');
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
      clearFornecedorForm();
      const data = await listFornecedores();
      setFornecedores(data.fornecedores);
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao salvar fornecedor.'));
    }
  }

  async function handleExcluirFornecedor(id: string) {
    try {
      await deleteFornecedor(id);
      if (editandoFornecedorId === id) clearFornecedorForm();
      const data = await listFornecedores();
      setFornecedores(data.fornecedores);
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao excluir fornecedor.'));
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

  return {
    fornecedores,
    setFornecedores,
    novoFornecedor,
    novoFornecedorCnpj,
    novoFornecedorEmail,
    editandoFornecedorId,
    propostaFile,
    propostaFornecedorId,
    uploading,
    confirmDeleteId,
    setNovoFornecedor,
    setNovoFornecedorCnpj,
    setNovoFornecedorEmail,
    setPropostaFornecedorId,
    setPropostaFile,
    setConfirmDeleteId,
    clearFornecedorForm,
    handleEditarFornecedor,
    handleCadastrarFornecedor,
    handleExcluirFornecedor,
    handleUploadProposta,
  };
}
