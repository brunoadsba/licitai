'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { toast } from 'sonner';
import { uploadDocument, listFornecedores } from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import { Button } from '@/components/ui/Button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import DropZone from '@/components/upload/DropZone';
import UploadTypeFields from '@/components/upload/UploadTypeFields';
import { useUploadAnalysisPipeline } from '@/components/upload/useUploadAnalysisPipeline';
import type { DocumentStatus, Fornecedor } from '@/types';

type UploadState = 'idle' | 'processing' | 'success' | 'error';

const STAGE_LABELS: Partial<Record<DocumentStatus, string>> = {
  uploaded: 'Enviando arquivo…',
  parsing: 'Extraindo texto e estrutura do documento…',
  analyzing: 'Iniciando análise com IA…',
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
  const [mode, setMode] = useState<'rapido' | 'avancado'>('rapido');
  const [analysisMode, setAnalysisMode] = useState<'economic' | 'multi_agent'>('economic');

  useUploadAnalysisPipeline({
    state,
    documentId,
    setState,
    setError,
    setCurrentStage,
    analysisMode,
  });

  useEffect(() => {
    listFornecedores()
      .then((data) => setFornecedores(data.fornecedores))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (mode === 'rapido') {
      setDocumentType('tr');
      setFornecedorId('');
    }
  }, [mode]);

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
    const type = mode === 'rapido' ? 'tr' : documentType;
    if (type === 'proposta' && !fornecedorId) {
      setError('Selecione o fornecedor da proposta antes de enviar.');
      return;
    }
    try {
      setState('processing');
      setCurrentStage('uploaded');
      setError(null);
      const result = await uploadDocument(selectedFile, {
        documentType: type,
        fornecedorId: type === 'proposta' ? fornecedorId : undefined,
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
          Enviar e revisar TR
        </h1>
        <p className="mt-1 text-sm text-content-muted">
          IA sugere; você decide. Só o aprovado vai ao SEI. Use Avançado para propostas ou para
          atualizar um TR existente (diff de versões).
        </p>
      </div>

      <Tabs
        value={mode}
        onValueChange={(v) => setMode(v as 'rapido' | 'avancado')}
      >
        <TabsList aria-label="Modo de envio">
          <TabsTrigger value="rapido">Rápido (TR)</TabsTrigger>
          <TabsTrigger value="avancado">Avançado</TabsTrigger>
        </TabsList>

        <TabsContent value="rapido" className="space-y-4">
          <p className="text-sm text-content-muted">
            Envie o Termo de Referência em PDF ou DOCX. O parse e a análise começam em seguida.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-content-muted">Modo de análise:</span>
            <Button
              type="button"
              size="sm"
              variant={analysisMode === 'economic' ? 'primary' : 'secondary'}
              onClick={() => setAnalysisMode('economic')}
            >
              Econômica (piloto)
            </Button>
            <Button
              type="button"
              size="sm"
              variant={analysisMode === 'multi_agent' ? 'primary' : 'secondary'}
              onClick={() => setAnalysisMode('multi_agent')}
            >
              Completa
            </Button>
          </div>
          <p className="text-[11px] text-content-subtle">
            Econômica = jurídico + Art. 6º (estrutural). Completa = quatro agentes.
          </p>
        </TabsContent>

        <TabsContent value="avancado" className="space-y-4">
          <div className="rounded-lg border border-line-subtle bg-white/[0.03] p-4">
            <p className="text-sm font-medium text-content-primary">Atualizar TR existente</p>
            <p className="mt-1 text-xs text-content-muted">
              Compare a versão antiga com a nova e, em seguida, analise o documento novo.
            </p>
            <Link href="/comparacao/versoes" className="mt-3 inline-flex">
              <Button type="button" size="sm" variant="secondary">
                Abrir diff de versões
              </Button>
            </Link>
          </div>
          <UploadTypeFields
            documentType={documentType}
            fornecedorId={fornecedorId}
            fornecedores={fornecedores}
            locked={locked}
            onDocumentTypeChange={setDocumentType}
            onFornecedorChange={setFornecedorId}
          />
        </TabsContent>
      </Tabs>

      <DropZone
        selectedFile={selectedFile}
        processing={state === 'processing'}
        success={state === 'success'}
        stageLabel={stageLabel}
        onFileSelect={validateAndSet}
        onUpload={handleUpload}
        onReset={resetUpload}
      />

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
    </div>
  );
}
