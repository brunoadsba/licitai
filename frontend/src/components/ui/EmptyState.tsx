import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

/** Estado vazio composto — nunca deixar tela em branco (DESIGN.md §5). */
export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center px-6 py-16 text-center', className)}>
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl border border-line-subtle bg-white/[0.03]">
        <Icon className="h-7 w-7 text-content-subtle" strokeWidth={1.5} aria-hidden />
      </div>
      <h2 className="text-base font-medium text-content-primary">{title}</h2>
      {description && <p className="mt-1.5 max-w-sm text-sm text-content-muted">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
