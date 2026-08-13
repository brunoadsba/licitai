'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { uploadDocument, getDocument, listFornecedores } from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import DropZone from '@/components/upload/DropZone';
import type { DocumentStatus, Fornecedor } from '@/types';

type UploadState = 'idle' | 'processing' | 'success' | 'error';

const STAGE_LABELS: Partial<Record<DocumentStatus, string>> = {
  uploaded: 'Enviando arquivo...',
  parsing: 'Extraindo texto e estrutura do documento...',
  analyzing: 'Análise em andamento...',
};

const POLL_INTERVAL_MS = 1000;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const MAX_SIZE = 50 * 1024 * 1024; // 50MB

export default function UploadPage() {
  const router = useRouter();
  const [state, setState] = useState<UploadState>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [documentType, setDocumentType] = useState<'tr' | 'proposta'>('tr');
  const [fornecedorId, setFornecedorId] = useState<string>('');
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [currentStage, setCurrentStage] = useState<DocumentStatus>('uploaded');

  useEffect(() => {
    listFornecedores()
      .then((data) => setFornecedores(data.fornecedores))
      .catch(() => {
        // Fornecedores são opcionais no fluxo TR — silencioso
      });
  }, []);

  // Polling do status real do documento após o envio
  useEffect(() => {
    if (state !== 'processing' || !documentId) return;

    const startedAt = Date.now();
    const interval = setInterval(async () => {
      try {
        const doc = await getDocument(documentId);
        setCurrentStage(doc.status);

        if (doc.status === 'error') {
          clearInterval(interval);
          setState('error');
          setError(doc.error_message || 'Falha no processamento do documento.');
        } else if (doc.status === 'parsed' || doc.status === 'completed') {
          clearInterval(interval);
          setState('success');
          setTimeout(() => router.push(`/analysis/${documentId}`), 1200);
        } else if (Date.now() - startedAt > POLL_TIMEOUT_MS) {
          clearInterval(interval);
          setState('error');
          setError(
            'O processamento demorou mais que o esperado. Verifique o status do documento na lista do Painel.'
          );
        }
      } catch {
        // Erros de polling são silenciosos — a última resposta válida continua valendo
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [state, documentId, router]);

  function validateAndSet(file: File) {
    setError(null);

    // Validação client-side (o backend valida novamente)
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError('Tipo de arquivo não permitido. Envie apenas PDF ou DOCX.');
      return;
    }

    if (file.size > MAX_SIZE) {
      setError(`Arquivo muito grande (${(file.size / 1024 / 1024).toFixed(1)}MB). Máximo: 50MB.`);
      return;
    }

    if (file.size === 0) {
      setError('Arquivo vazio não é permitido.');
      return;
    }

    setSelectedFile(file);
  }

  async function handleUpload() {
    if (!selectedFile) return;

    if (documentType === 'proposta' && !fornecedorId) {
      setError('Selecione o fornecedor da proposta antes de enviar.');
      return;
    }

    try {
      setState('processing');
      setCurrentStage('uploaded');
      setError(null);

      const result = await uploadDocument(selectedFile, {
        documentType,
        fornecedorId: documentType === 'proposta' ? fornecedorId : undefined,
      });

      setDocumentId(result.id);
    } catch (err) {
      setState('error');
      setError(err instanceof Error ? err.message : 'Erro ao enviar documento.');
    }
  }

  function resetUpload() {
    setState('idle');
    setSelectedFile(null);
    setError(null);
    setDocumentId(null);
    setCurrentStage('uploaded');
  }

  const uploadError = error ? getErrorMessage(error, 'upload') : null;
  const stageLabel = STAGE_LABELS[currentStage] || 'Processando documento...';

  return (
    <div className="max-w-2xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Enviar Documento</h1>
        <p className="text-gray-400 mt-1 text-sm">
          Envie um Termo de Referência em PDF ou DOCX para análise automática.
        </p>
      </div>

      {/* Tipo de documento */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="document-type" className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
            Tipo de documento
          </label>
          <select
            id="document-type"
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value as 'tr' | 'proposta')}
            disabled={state === 'processing' || state === 'success'}
            className="input-field"
          >
            <option value="tr">Termo de Referência</option>
            <option value="proposta">Proposta de fornecedor</option>
          </select>
        </div>

        {documentType === 'proposta' && (
          <div>
            <label htmlFor="fornecedor" className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
              Fornecedor
            </label>
            <select
              id="fornecedor"
              value={fornecedorId}
              onChange={(e) => setFornecedorId(e.target.value)}
              disabled={state === 'processing' || state === 'success'}
              className="input-field"
            >
              <option value="">Selecione o fornecedor...</option>
              {fornecedores.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.nome}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Drop Zone */}
      <DropZone
        selectedFile={selectedFile}
        processing={state === 'processing'}
        success={state === 'success'}
        stageLabel={stageLabel}
        onFileSelect={validateAndSet}
        onUpload={handleUpload}
        onReset={resetUpload}
      />

      {/* Mensagem de erro */}
      {uploadError && (
        <AlertBanner
          variant="error"
          title={uploadError.title}
          action={
            <button onClick={resetUpload} className="btn-secondary text-xs">
              Tentar Novamente
            </button>
          }
        >
          {uploadError.message}
        </AlertBanner>
      )}

      {/* Instruções */}
      <div className="glass-card p-6">
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Como funciona</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { step: '1', title: 'Envie', desc: 'Faça upload do Termo de Referência em PDF ou DOCX.' },
            { step: '2', title: 'Análise', desc: 'A IA analisa cada item jurídica, técnica e redacionalmente.' },
            { step: '3', title: 'Relatório', desc: 'Receba correções no formato DE → PARA com fundamentação.' },
          ].map((item) => (
            <div key={item.step} className="flex gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary-500/15 text-primary-400 font-bold text-sm flex items-center justify-center shrink-0">
                {item.step}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-300">{item.title}</p>
                <p className="text-xs text-gray-500 mt-0.5">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
