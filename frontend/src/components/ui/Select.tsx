'use client';

import * as React from 'react';
import * as SelectPrimitive from '@radix-ui/react-select';
import { Check, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

const Select = SelectPrimitive.Root;
const SelectValue = SelectPrimitive.Value;

function SelectTrigger({
  className,
  children,
  ...props
}: React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>) {
  return (
    <SelectPrimitive.Trigger
      className={cn(
        'flex h-10 w-full items-center justify-between gap-2 rounded-lg border border-line-strong',
        'bg-white/[0.03] px-3.5 py-2 text-sm text-content-primary outline-none transition-all duration-150',
        'placeholder:text-content-subtle',
        'focus:border-accent-500/45 focus:ring-[3px] focus:ring-accent-500/20',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'data-[placeholder]:text-content-subtle [&>span]:truncate',
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDown className="h-4 w-4 shrink-0 text-content-muted" aria-hidden />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  );
}

function SelectContent({ className, children, position = 'popper', ...props }: React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        position={position}
        className={cn(
          'relative z-50 max-h-72 min-w-[8rem] overflow-hidden rounded-lg border border-line-subtle bg-elevated shadow-dialog',
          'data-[state=open]:animate-in',
          position === 'popper' && 'w-full min-w-[var(--radix-select-trigger-width)]',
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport
          className={cn('p-1', position === 'popper' && 'h-[var(--radix-select-content-available-height)]')}
        >
          {children}
        </SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
}

function SelectItem({ className, children, ...props }: React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      className={cn(
        'relative flex w-full cursor-default select-none items-center rounded-md py-2 pl-3 pr-8 text-sm outline-none',
        'focus:bg-white/[0.06] data-disabled:pointer-events-none data-disabled:opacity-50',
        'data-[state=checked]:text-accent-400',
        className,
      )}
      {...props}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
      <span className="absolute right-2.5 flex h-4 w-4 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <Check className="h-4 w-4" aria-hidden />
        </SelectPrimitive.ItemIndicator>
      </span>
    </SelectPrimitive.Item>
  );
}

function SelectLabel({ className, ...props }: React.ComponentPropsWithoutRef<typeof SelectPrimitive.Label>) {
  return (
    <SelectPrimitive.Label
      className={cn('px-3 py-1.5 text-[11px] font-medium uppercase tracking-wide text-content-subtle', className)}
      {...props}
    />
  );
}

export { Select, SelectValue, SelectTrigger, SelectContent, SelectItem, SelectLabel };
