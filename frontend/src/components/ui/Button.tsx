'use client';

import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary:
    'bg-accent-700 text-white hover:not-disabled:bg-accent-800 shadow-rim',
  secondary:
    'border border-line-strong bg-white/[0.04] text-content-secondary hover:not-disabled:bg-white/[0.07] hover:not-disabled:border-white/20 hover:not-disabled:text-content-primary',
  ghost:
    'text-content-muted hover:not-disabled:bg-white/[0.06] hover:not-disabled:text-content-primary',
  danger:
    'border border-red-500/40 bg-red-500/15 text-red-400 hover:not-disabled:bg-red-500/25',
};

const sizeClasses: Record<Size, string> = {
  sm: 'h-8 px-3 text-xs rounded-md gap-1.5',
  md: 'h-10 px-4 text-sm rounded-lg gap-2',
  lg: 'h-11 px-6 text-sm rounded-lg gap-2',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading = false, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        // Estados base — DESIGN.md §5: active scale, focus-visible ring, disabled
        'inline-flex select-none items-center justify-center whitespace-nowrap font-medium',
        'outline-none transition-all duration-150 ease-out',
        'active:not-disabled:scale-[0.98]',
        'focus-visible:ring-2 focus-visible:ring-accent-500/60 focus-visible:ring-offset-2 focus-visible:ring-offset-canvas',
        'disabled:pointer-events-none disabled:opacity-50',
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  ),
);
Button.displayName = 'Button';
