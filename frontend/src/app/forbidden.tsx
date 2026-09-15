'use client';

import Link from 'next/link';
import { ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function Forbidden() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-xl border border-amber-500/25 bg-amber-500/10">
        <ShieldAlert className="h-7 w-7 text-amber-400" strokeWidth={1.5} aria-hidden />
      </div>
      <h1 className="text-xl font-semibold tracking-tight text-content-primary">
        Sem acesso a esta página
      </h1>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-content-muted">
        Você não tem permissão para ver este conteúdo. Volte ao painel ou peça
        acesso ao responsável.
      </p>
      <div className="mt-6 flex gap-3">
        <Link href="/">
          <Button variant="secondary">Voltar ao painel</Button>
        </Link>
      </div>
    </div>
  );
}
