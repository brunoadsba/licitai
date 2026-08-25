import { LoaderCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

const sizes = {
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-7 w-7',
} as const;

export function Spinner({ size = 'md', className, label }: { size?: keyof typeof sizes; className?: string; label?: string }) {
  return (
    <span role="status" aria-label={label ?? 'Carregando'} className="inline-flex">
      <LoaderCircle className={cn('animate-spin text-current', sizes[size], className)} aria-hidden />
    </span>
  );
}
