'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { uploadDocument, getDocument, listFornecedores } from '@/lib/api';
import { startPolling } from '@/lib/polling';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import { Button } from '@/components/ui/Button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';
import DropZone from '@/components/upload/DropZone';
import type { DocumentStatus, Fornecedor } from '@/types';

type UploadState = 'idle' | 'processing' | 'success' | 'error';

const STAGE_LABELS: Partial<Record<DocumentStatus, string>> = {
  uploaded: 'Enviando arquivo…',
  parsing: 'Extraindo texto e estrutura do documento…',
  analyzing: 'Análise em andamento…',
};

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

    const { cancel } = startPolling(
      () => getDocument(documentId, { skipCache: true }),
      (doc) =>
        doc.status === 'error' || doc.status === 'parsed' || doc.status === 'completed',
      {
        initialIntervalMs: 1000,
        maxIntervalMs: 8000,
        deadlineMs: POLL_TIMEOUT_MS,
        maxFailures: 10,
        onResult: (doc) => {
          setCurrentStage(doc.status);
          if (doc.status === 'error') {
            setState('error');
            setError(doc.error_message || 'Falha no processamento do documento.');
            return true;
          }
          if (doc.status === 'parsed' || doc.status === 'completed') {
            setState('success');
            toast.success('Documento processado');
            setTimeout(() => router.push(`/analysis/${documentId}`), 1200);
            return true;
          }
        },
        onDeadline: () => {
          setState('error');
          setError(
            'O processamento demorou mais que o esperado. Verifique o status do documento na lista do Painel.',
          );
        },
        onMaxFailures: () => {
          setState('error');
          setError('Falha ao acompanhar o processamento. Tente novamente ou verifique o Painel.');
        },
      }
    );

    return () => cancel();
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
      toast.error('Falha no envio do documento');
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
  const stageLabel = STAGE_LABELS[currentStage] || 'Processando documento…';
  const locked = state === 'processing' || state === 'success';

  return (
    <div className="animate-fade-in mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-content-primary">Enviar Documento</h1>
        <p className="mt-1 text-sm text-content-muted">
          Envie um Termo de Referência em PDF ou DOCX para análise automática.
        </p>
      </div>

      {/* Tipo de documento */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <span className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
            Tipo de documento
          </span>
          <Select
            value={documentType}
            onValueChange={(v) => setDocumentType(v as 'tr' | 'proposta')}
            disabled={locked}
          >
            <SelectTrigger aria-label="Tipo de documento">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="tr">Termo de Referência</SelectItem>
              <SelectItem value="proposta">Proposta de fornecedor</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {documentType === 'proposta' && (
          <div>
            <span className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
              Fornecedor
            </span>
            <Select value={fornecedorId} onValueChange={setFornecedorId} disabled={locked}>
              <SelectTrigger aria-label="Fornecedor da proposta">
                <SelectValue placeholder="Selecione o fornecedor…" />
              </SelectTrigger>
              <SelectContent>
                {fornecedores.map((f) => (
                  <SelectItem key={f.id} value={f.id}>
                    {f.nome}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
            <Button size="sm" variant="secondary" onClick={resetUpload}>
              Tentar Novamente
            </Button>
          }
        >
          {uploadError.message}
        </AlertBanner>
      )}

      {/* Instruções */}
      <div className="glass-card p-6">
        <h2 className="mb-4 text-sm font-semibold text-content-primary">Como funciona</h2>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {[
            { step: '1', title: 'Envie', desc: 'Faça upload do Termo de Referência em PDF ou DOCX.' },
            { step: '2', title: 'Análise', desc: 'A IA analisa cada item jurídica, técnica e redacionalmente.' },
            { step: '3', title: 'Relatório', desc: 'Receba correções no formato DE → PARA com fundamentação.' },
          ].map((item) => (
            <div key={item.step} className="flex gap-3">
              <div className="tnum flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-accent-500/25 bg-accent-500/10 text-sm font-semibold text-accent-400">
                {item.step}
              </div>
              <div>
                <p className="text-sm font-medium text-content-primary">{item.title}</p>
                <p className="mt-0.5 text-xs text-content-muted">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
