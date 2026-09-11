'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import { uploadDocument, listFornecedores } from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import { Button } from '@/components/ui/Button';
import DropZone from '@/components/upload/DropZone';
import UploadTypeFields from '@/components/upload/UploadTypeFields';
import { useUploadAnalysisPipeline } from '@/components/upload/useUploadAnalysisPipeline';
import type { DocumentStatus, Fornecedor } from '@/types';
import { cn } from '@/lib/utils';

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
  const [documentType, setDocumentType] = useState<'tr' | 'proposta'>('tr');
  const [fornecedorId, setFornecedorId] = useState('');
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [currentStage, setCurrentStage] = useState<DocumentStatus>('uploaded');
  /** Default piloto: econômico (jurídico + Art. 6). Completo só em opções. */
  const [analysisMode, setAnalysisMode] = useState<'economic' | 'multi_agent'>('economic');
  const [optionsOpen, setOptionsOpen] = useState(false);

  useUploadAnalysisPipeline({
    state,
    documentId,
    setState,
    setError,
    setCurrentStage,
    analysisMode,
    documentType,
  });

  useEffect(() => {
    listFornecedores()
      .then((data) => setFornecedores(data.fornecedores))
      .catch(() => {});
  }, []);

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
    if (documentType === 'proposta' && !fornecedorId) {
      setError('Selecione o fornecedor da proposta antes de enviar.');
      setOptionsOpen(true);
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
        <h1 className="text-2xl font-semibold tracking-tight text-content-primary">
          Enviar TR
        </h1>
        <p className="mt-1 text-sm text-content-muted">
          Solte o Termo de Referência. A análise começa em seguida; você revisa o que importa e
          copia só o aprovado para o SEI.
        </p>
      </div>

      <DropZone
        selectedFile={selectedFile}
        processing={state === 'processing'}
        success={state === 'success'}
        stageLabel={stageLabel}
        successTitle={
          documentType === 'proposta' ? 'Proposta enviada!' : 'Análise iniciada!'
        }
        successSubtitle={
          documentType === 'proposta'
            ? 'Abrindo Comparações…'
            : 'Abrindo a tela de análise…'
        }
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
          <div className="space-y-5 border-t border-line-subtle px-4 py-4">
            <div className="space-y-2">
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

            <div className="space-y-2">
              <p className="text-xs font-medium text-content-secondary">Tipo de documento</p>
              <UploadTypeFields
                documentType={documentType}
                fornecedorId={fornecedorId}
                fornecedores={fornecedores}
                locked={locked}
                onDocumentTypeChange={setDocumentType}
                onFornecedorChange={setFornecedorId}
              />
            </div>

            <div className="rounded-md border border-line-subtle bg-canvas/40 p-3">
              <p className="text-sm font-medium text-content-primary">Atualizar TR existente</p>
              <p className="mt-1 text-xs text-content-muted">
                Compare a versão antiga com a nova e depois analise o documento novo.
              </p>
              <Link href="/comparacao/versoes" className="mt-3 inline-flex">
                <Button type="button" size="sm" variant="secondary">
                  Abrir comparação de versões
                </Button>
              </Link>
            </div>
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
