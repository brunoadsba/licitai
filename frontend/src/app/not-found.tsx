import Link from 'next/link';
import { FileQuestion } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-xl border border-line-subtle bg-white/[0.03]">
        <FileQuestion className="h-7 w-7 text-content-subtle" strokeWidth={1.5} aria-hidden />
      </div>
      <h1 className="text-xl font-semibold tracking-tight text-content-primary">
        Página não encontrada
      </h1>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-content-muted">
        O endereço acessado não existe ou o recurso foi removido.
      </p>
      <div className="mt-6">
        <Link href="/">
          <Button>Voltar ao Painel</Button>
        </Link>
      </div>
    </div>
  );
}
