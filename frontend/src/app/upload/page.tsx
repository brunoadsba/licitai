'use client';

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import { uploadDocument } from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import { Button } from '@/components/ui/Button';
import DropZone from '@/components/upload/DropZone';
import UploadTypeFields, {
  type DocumentClassification,
} from '@/components/upload/UploadTypeFields';
import { useUploadAnalysisPipeline } from '@/components/upload/useUploadAnalysisPipeline';
import type { DocumentStatus } from '@/types';
import { cn } from '@/lib/utils';
import { copy } from '@/lib/copy';

type UploadState = 'idle' | 'processing' | 'success' | 'error';

const STAGE_LABELS: Partial<Record<DocumentStatus, string>> = {
  uploaded: 'Enviando arquivo…',
  parsing: 'Lendo PDF e estrutura…',
  analyzing: 'Analisando partes obrigatórias do TR e riscos jurídicos…',
};

const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const MAX_SIZE = 50 * 1024 * 1024;

export default function UploadPage() {
  const [state, setState] = useState<UploadState>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [classification, setClassification] = useState<DocumentClassification | ''>('');
  const [currentStage, setCurrentStage] = useState<DocumentStatus>('uploaded');
  const [analysisMode, setAnalysisMode] = useState<'economic' | 'multi_agent'>('economic');
  const [optionsOpen, setOptionsOpen] = useState(false);

  useUploadAnalysisPipeline({
    state,
    documentId,
    setState,
    setError,
    setCurrentStage,
    analysisMode,
  });

  function validateAndSet(file: File) {
    setError(null);
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
    if (!classification) {
      setError('Selecione a classificação do documento antes de enviar.');
      return;
    }
    try {
      setState('processing');
      setCurrentStage('uploaded');
      setError(null);
      const result = await uploadDocument(selectedFile, {
        documentType: 'tr',
        classification,
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
        <h1 className="text-2xl font-semibold tracking-tight text-content-primary">
          {copy.upload.title}
        </h1>
        <p className="mt-1 text-sm text-content-muted">{copy.upload.subtitle}</p>
      </div>

      <UploadTypeFields
        classification={classification}
        locked={locked}
        onClassificationChange={setClassification}
      />

      <DropZone
        selectedFile={selectedFile}
        processing={state === 'processing'}
        success={state === 'success'}
        stageLabel={stageLabel}
        successTitle="Análise iniciada!"
        successSubtitle="Abrindo a tela de análise…"
        onFileSelect={validateAndSet}
        onUpload={handleUpload}
        onReset={resetUpload}
      />

      <div className="rounded-lg border border-line-subtle bg-surface/40" data-testid="options-advanced">
        <button
          type="button"
          onClick={() => setOptionsOpen((v) => !v)}
          disabled={locked}
          data-testid="options-advanced-toggle"
          className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm font-medium text-content-primary outline-none hover:bg-white/[0.03] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent-500/60 disabled:opacity-50"
          aria-expanded={optionsOpen}
        >
          Opções avançadas
          <ChevronDown
            className={cn('h-4 w-4 text-content-muted transition-transform', optionsOpen && 'rotate-180')}
            aria-hidden
          />
        </button>
        {optionsOpen && (
          <div className="space-y-2 border-t border-line-subtle px-4 py-4">
            <p className="text-xs font-medium text-content-secondary">Abrangência da análise</p>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant={analysisMode === 'economic' ? 'primary' : 'secondary'}
                disabled={locked}
                data-testid="analysis-mode-essential"
                onClick={() => setAnalysisMode('economic')}
              >
                Revisão essencial
              </Button>
              <Button
                type="button"
                size="sm"
                variant={analysisMode === 'multi_agent' ? 'primary' : 'secondary'}
                disabled={locked}
                data-testid="analysis-mode-full"
                onClick={() => setAnalysisMode('multi_agent')}
              >
                Revisão completa
              </Button>
            </div>
            <p className="text-[11px] text-content-subtle">
              Essencial = estrutura do TR + riscos jurídicos. Completa = também técnico e
              redação.
            </p>
          </div>
        )}
      </div>

      {uploadError && (
        <AlertBanner
          variant="error"
          title={uploadError.title}
          action={
            <Button size="sm" variant="secondary" onClick={resetUpload}>
              Tentar novamente
            </Button>
          }
        >
          {uploadError.message}
        </AlertBanner>
      )}
    </div>
  );
}
