'use client';

import { forwardRef, type TextareaHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error = false, ...props }, ref) => (
    <textarea
      ref={ref}
      aria-invalid={error || undefined}
      className={cn(
        'w-full rounded-lg border bg-white/[0.03] px-3.5 py-2.5 text-sm text-content-primary',
        'placeholder:text-content-subtle outline-none transition-all duration-150',
        'focus:border-accent-500/45 focus:ring-[3px] focus:ring-accent-500/20',
        'disabled:cursor-not-allowed disabled:opacity-50',
        error
          ? 'border-red-500/50 focus:border-red-500/60 focus:ring-red-500/20'
          : 'border-line-strong',
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = 'Textarea';
