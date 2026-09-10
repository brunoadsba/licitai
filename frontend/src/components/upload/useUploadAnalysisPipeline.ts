'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { getDocument, startAnalysis } from '@/lib/api';
import { pollUntil } from '@/lib/polling';
import type { DocumentStatus } from '@/types';

const POLL_TIMEOUT_MS = 5 * 60 * 1000;

type UploadState = 'idle' | 'processing' | 'success' | 'error';

/**
 * Após upload: aguarda parse, inicia análise e redireciona para /analysis/[id].
 */
export function useUploadAnalysisPipeline(options: {
  state: UploadState;
  documentId: string | null;
  setState: (s: UploadState) => void;
  setError: (msg: string | null) => void;
  setCurrentStage: (s: DocumentStatus) => void;
  analysisMode?: 'economic' | 'multi_agent' | 'single';
}) {
  const router = useRouter();
  const { state, documentId, setState, setError, setCurrentStage, analysisMode = 'economic' } =
    options;

  useEffect(() => {
    if (state !== 'processing' || !documentId) return;
    let cancelled = false;

    (async () => {
      const doc = await pollUntil(
        () => getDocument(documentId, { skipCache: true }),
        (d) => d.status === 'error' || d.status === 'parsed' || d.status === 'completed',
        {
          initialIntervalMs: 1000,
          maxIntervalMs: 8000,
          deadlineMs: POLL_TIMEOUT_MS,
          maxFailures: 10,
          onResult: (d) => setCurrentStage(d.status),
          onDeadline: () => {
            if (cancelled) return;
            setState('error');
            setError(
              'O processamento demorou mais que o esperado. Verifique o status do documento na lista do Painel.',
            );
          },
          onMaxFailures: () => {
            if (cancelled) return;
            setState('error');
            setError(
              'Falha ao acompanhar o processamento. Tente novamente ou verifique o Painel.',
            );
          },
        },
      );

      if (cancelled || !doc) return;
      if (doc.status === 'error') {
        setState('error');
        setError(doc.error_message || 'Falha no processamento do documento.');
        return;
      }

      setCurrentStage('analyzing');
      try {
        await startAnalysis(documentId, analysisMode);
        if (cancelled) return;
        setState('success');
        toast.success('Documento processado — análise iniciada');
        setTimeout(() => {
          if (!cancelled) router.push(`/analysis/${documentId}`);
        }, 1200);
      } catch (err) {
        if (cancelled) return;
        setState('error');
        setError(
          err instanceof Error
            ? err.message
            : 'Documento processado, mas falhou ao iniciar a análise.',
        );
        toast.error('Falha ao iniciar a análise');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [state, documentId, router, setState, setError, setCurrentStage, analysisMode]);
}
