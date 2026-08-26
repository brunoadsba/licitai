'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Check, FileText, ClipboardCopy, Sparkles } from 'lucide-react';
import DropZone from '@/components/upload/DropZone';
import CorrectionCard from '@/components/analysis/CorrectionCard';
import { Button } from '@/components/ui/Button';
import AlertBanner from '@/components/ui/AlertBanner';
import { uploadDocument, startAnalysis, getAnalysis } from '@/lib/api';
import { getErrorMessage } from '@/lib/errors';
import type { CorrectionResponse } from '@/types';

type Step = 1 | 2 | 3;

export default function WizardPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [corrections, setCorrections] = useState<CorrectionResponse[]>([]);

  async function handleUpload() {
    if (!file) return;
    setError(null);
    try {
      const doc = await uploadDocument(file, { documentType: 'tr' });
      setStep(2);
      const start = await startAnalysis(doc.id);
      setAnalysisId(start.analysis_id);
      toast.success('Documento enviado — análise iniciada');
      for (let i = 0; i < 60; i++) {
        const a = await getAnalysis(start.analysis_id);
        if (a.status === 'completed') {
          setCorrections(a.corrections);
          setStep(3);
          toast.success(`${a.corrections.length} correções prontas para cópia`);
          break;
        }
        if (a.status === 'error') {
          setError(a.error_message || 'Falha na análise');
          break;
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
    } catch (e) {
      setError(getErrorMessage(e, 'upload').message);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="flex items-center gap-2">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div className={`flex h-8 w-8 items-center justify-center rounded-full border text-sm font-semibold ${step >= s ? 'border-accent-500 bg-accent-500/20 text-accent-400' : 'border-line-subtle text-content-subtle'}`}>
              {step > s ? <Check className="h-4 w-4" /> : s}
            </div>
            {s < 3 && <div className={`h-px w-12 ${step > s ? 'bg-accent-500/50' : 'bg-line-subtle'}`} />}
          </div>
        ))}
        <span className="ml-4 text-sm text-content-muted">
          {step === 1 && 'Escolher TR'}
          {step === 2 && 'Ver correções'}
          {step === 3 && 'Copiar para SEI'}
        </span>
      </div>

      {step === 1 && (
        <div className="space-y-4">
          <h1 className="flex items-center gap-2 text-xl font-semibold text-content-primary"><FileText className="h-5 w-5" /> Escolher TR</h1>
          <p className="text-sm text-content-muted">Envie o Termo de Referência em PDF ou DOCX. Um clique e a análise começa.</p>
          <DropZone selectedFile={file} processing={false} success={false} stageLabel="" onFileSelect={setFile} onUpload={handleUpload} onReset={() => setFile(null)} />
          {error && <AlertBanner variant="error" title="Erro no envio">{error}</AlertBanner>}
          <div className="flex gap-2">
            <Button onClick={handleUpload} disabled={!file}><Sparkles className="h-4 w-4" /> Analisar agora</Button>
            <Button variant="secondary" onClick={() => router.push('/upload')}>Modo avançado</Button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="glass-card p-8 text-center">
          <p className="animate-pulse text-sm text-content-muted">Analisando itens com 4 agentes — aguarde até 60s…</p>
          {error && <AlertBanner variant="error" title="Falha na análise">{error}</AlertBanner>}
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-content-primary"><ClipboardCopy className="h-5 w-5" /> Correções prontas — 1 clique para o SEI</h2>
          <p className="text-sm text-content-muted">Cada card já formata <span className="font-mono text-accent-400">PARA + Fundamento + Justificativa</span> com confiança.</p>
          {corrections.length === 0 ? (
            <AlertBanner variant="info" title="Nenhuma correção crítica encontrada">O TR parece conforme — confira o relatório completo.</AlertBanner>
          ) : (
            corrections.map((c, i) => <CorrectionCard key={c.id} correction={c} index={i} />)
          )}
          <Button variant="secondary" onClick={() => analysisId && router.push(`/report/${analysisId}`)}>Ver relatório completo</Button>
        </div>
      )}
    </div>
  );
}
