import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export type Tone =
  | 'neutral'
  | 'info'
  | 'low'
  | 'medium'
  | 'high'
  | 'critical'
  | 'juridica'
  | 'tecnica'
  | 'redacao'
  | 'estrutural'
  | 'accent';

/** Claro: pastel + texto 800/900. Escuro: /10 + texto-400. */
const toneClasses: Record<Tone, string> = {
  neutral:
    'border-slate-300 bg-slate-100 text-slate-800 dark:border-white/10 dark:bg-white/[0.06] dark:text-content-secondary',
  info:
    'border-sky-700/25 bg-sky-100 text-sky-900 dark:border-sky-500/20 dark:bg-sky-500/10 dark:text-sky-400',
  low:
    'border-green-700/25 bg-green-100 text-green-900 dark:border-green-500/20 dark:bg-green-500/10 dark:text-green-400',
  medium:
    'border-amber-700/30 bg-amber-100 text-amber-950 dark:border-yellow-500/20 dark:bg-yellow-500/10 dark:text-yellow-400',
  high:
    'border-orange-700/30 bg-orange-100 text-orange-950 dark:border-orange-500/20 dark:bg-orange-500/10 dark:text-orange-400',
  critical:
    'border-red-700/30 bg-red-100 text-red-950 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-400',
  juridica:
    'border-purple-700/25 bg-purple-100 text-purple-900 dark:border-purple-500/20 dark:bg-purple-500/10 dark:text-purple-400',
  tecnica:
    'border-cyan-700/25 bg-cyan-100 text-cyan-900 dark:border-cyan-500/20 dark:bg-cyan-500/10 dark:text-cyan-400',
  redacao:
    'border-amber-700/25 bg-amber-100 text-amber-950 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-400',
  estrutural:
    'border-teal-700/25 bg-teal-100 text-teal-900 dark:border-teal-500/20 dark:bg-teal-500/10 dark:text-teal-400',
  accent:
    'border-accent-700/30 bg-accent-100 text-accent-900 dark:border-accent-500/25 dark:bg-accent-500/10 dark:text-accent-400',
};

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

export function Badge({ className, tone = 'neutral', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5',
        'text-[11px] font-medium uppercase tracking-wide',
        toneClasses[tone],
        className,
      )}
      {...props}
    />
  );
}
