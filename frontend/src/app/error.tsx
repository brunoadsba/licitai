'use client';

import { useEffect } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[app] erro não tratado:', error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-xl border border-red-500/25 bg-red-500/10">
        <AlertTriangle className="h-7 w-7 text-red-400" strokeWidth={1.5} aria-hidden />
      </div>
      <h1 className="text-xl font-semibold tracking-tight text-content-primary">
        Algo deu errado
      </h1>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-content-muted">
        Ocorreu um erro inesperado nesta tela. Você pode tentar novamente — se persistir,
        recarregue a página.
      </p>
      {error.digest && (
        <p className="mt-3 font-mono text-xs text-content-subtle">ref: {error.digest}</p>
      )}
      <div className="mt-6 flex gap-3">
        <Button onClick={reset} variant="secondary">
          <RotateCcw className="h-4 w-4" aria-hidden />
          Tentar novamente
        </Button>
      </div>
    </div>
  );
}
