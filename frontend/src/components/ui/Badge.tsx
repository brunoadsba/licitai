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

const toneClasses: Record<Tone, string> = {
  neutral: 'border-white/10 bg-white/[0.06] text-content-secondary',
  info: 'border-sky-500/20 bg-sky-500/10 text-sky-400',
  low: 'border-green-500/20 bg-green-500/10 text-green-400',
  medium: 'border-yellow-500/20 bg-yellow-500/10 text-yellow-400',
  high: 'border-orange-500/20 bg-orange-500/10 text-orange-400',
  critical: 'border-red-500/20 bg-red-500/10 text-red-400',
  juridica: 'border-purple-500/20 bg-purple-500/10 text-purple-400',
  tecnica: 'border-cyan-500/20 bg-cyan-500/10 text-cyan-400',
  redacao: 'border-amber-500/20 bg-amber-500/10 text-amber-400',
  estrutural: 'border-teal-500/20 bg-teal-500/10 text-teal-400',
  accent: 'border-accent-500/25 bg-accent-500/10 text-accent-400',
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
