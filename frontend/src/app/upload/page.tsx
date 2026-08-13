'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { uploadDocument, getDocument, listFornecedores } from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import type { DocumentStatus, Fornecedor } from '@/types';

type UploadState = 'idle' | 'dragging' | 'processing' | 'success' | 'error';

const STAGE_LABELS: Partial<Record<DocumentStatus, string>> = {
  uploaded: 'Enviando arquivo...',
  parsing: 'Extraindo texto e estrutura do documento...',
  analyzing: 'Análise em andamento...',
};

const POLL_INTERVAL_MS = 1000;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

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

  const ALLOWED_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ];
  const MAX_SIZE = 50 * 1024 * 1024; // 50MB

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

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setState('dragging');
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setState('idle');
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setState('idle');

    const file = e.dataTransfer.files[0];
    if (file) validateAndSet(file);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) validateAndSet(file);
  }, []);

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

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`glass-card p-12 text-center transition-all duration-300 ${
          state === 'dragging'
            ? 'border-primary-500/50 bg-primary-500/5 scale-[1.02]'
            : 'hover:border-white/10'
        } ${state === 'success' ? 'border-green-500/30' : ''}`}
      >
        {state === 'processing' ? (
          /* Processamento com etapas reais */
          <div aria-live="polite" className="space-y-6">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-primary-500/10 flex items-center justify-center">
              <svg className="w-8 h-8 text-primary-400 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>
            <div>
              <p className="text-white font-semibold">{stageLabel}</p>
              <p className="text-gray-500 text-sm mt-1">
                Isso pode levar alguns minutos dependendo do tamanho do documento.
              </p>
            </div>
          </div>
        ) : state === 'success' ? (
          /* Sucesso */
          <div className="space-y-4">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-green-500/10 flex items-center justify-center">
              <svg className="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </div>
            <div>
              <p className="text-green-400 font-semibold">Documento enviado com sucesso!</p>
              <p className="text-gray-500 text-sm mt-1">Redirecionando para análise...</p>
            </div>
          </div>
        ) : (
          /* Área de drop */
          <>
            <div className="w-16 h-16 mx-auto rounded-2xl bg-primary-500/10 flex items-center justify-center mb-6">
              <svg className="w-8 h-8 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>

            {selectedFile ? (
              <div className="space-y-4">
                <div className="glass-card inline-flex items-center gap-3 px-5 py-3">
                  <span className={`text-xs font-bold uppercase px-2 py-1 rounded ${
                    selectedFile.name.endsWith('.pdf')
                      ? 'bg-red-500/15 text-red-400'
                      : 'bg-blue-500/15 text-blue-400'
                  }`}>
                    {selectedFile.name.split('.').pop()}
                  </span>
                  <div className="text-left">
                    <p className="text-sm text-white font-medium truncate max-w-xs">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-center gap-3">
                  <button onClick={handleUpload} className="btn-primary">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                    </svg>
                    Enviar e Analisar
                  </button>
                  <button onClick={resetUpload} className="btn-secondary">
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              <>
                <p className="text-gray-300 font-medium mb-2">
                  Arraste o arquivo aqui ou clique para selecionar
                </p>
                <p className="text-gray-600 text-sm mb-6">
                  Formatos aceitos: PDF, DOCX • Máximo: 50MB
                </p>
                <label className="btn-secondary cursor-pointer">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
                  </svg>
                  Selecionar Arquivo
                  <input
                    type="file"
                    accept=".pdf,.docx"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </label>
              </>
            )}
          </>
        )}
      </div>

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