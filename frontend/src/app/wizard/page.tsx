'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** Wizard legado — redireciona para o fluxo rápido em /upload. */
export default function WizardRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/upload');
  }, [router]);

  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <p className="text-sm text-content-muted">Redirecionando para Enviar Documento…</p>
    </div>
  );
}
