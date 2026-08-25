'use client';

import { forwardRef, type InputHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error = false, ...props }, ref) => (
    <input
      ref={ref}
      aria-invalid={error || undefined}
      className={cn(
        'h-10 w-full rounded-lg border bg-white/[0.03] px-3.5 text-sm text-content-primary',
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
Input.displayName = 'Input';
