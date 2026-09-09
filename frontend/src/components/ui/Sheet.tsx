'use client';

import * as React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

const Sheet = DialogPrimitive.Root;
const SheetTrigger = DialogPrimitive.Trigger;
const SheetClose = DialogPrimitive.Close;
const SheetPortal = DialogPrimitive.Portal;

function SheetOverlay({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>) {
  return (
    <DialogPrimitive.Overlay
      className={cn(
        'fixed inset-0 z-50 bg-black/70 backdrop-blur-[4px]',
        'data-[state=open]:animate-overlayIn',
        className,
      )}
      {...props}
    />
  );
}

type SheetSide = 'left' | 'right' | 'bottom';

interface SheetContentProps extends React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
  side?: SheetSide;
  hideClose?: boolean;
}

const sideClasses: Record<SheetSide, string> = {
  left: 'inset-y-0 left-0 h-full w-72 max-w-[85vw] border-r data-[state=open]:animate-contentIn',
  right: 'inset-y-0 right-0 h-full w-full max-w-md border-l sm:max-w-lg data-[state=open]:animate-contentIn',
  bottom:
    'inset-x-0 bottom-0 h-[min(92dvh,720px)] w-full rounded-t-xl border-t data-[state=open]:animate-contentIn',
};

function SheetContent({
  side = 'left',
  className,
  children,
  hideClose = false,
  ...props
}: SheetContentProps) {
  return (
    <SheetPortal>
      <SheetOverlay />
      <DialogPrimitive.Content
        className={cn(
          'fixed z-50 flex flex-col border-line-subtle bg-panel shadow-drawer outline-none',
          sideClasses[side],
          className,
        )}
        {...props}
      >
        {children}
        {!hideClose && (
          <DialogPrimitive.Close
            className="absolute right-3 top-3 rounded-md p-2 text-content-muted outline-none transition-colors hover:bg-white/[0.06] hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
            aria-label="Fechar"
          >
            <X className="h-5 w-5" aria-hidden />
          </DialogPrimitive.Close>
        )}
      </DialogPrimitive.Content>
    </SheetPortal>
  );
}

function SheetHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('border-b border-line-subtle p-4 pr-12', className)} {...props} />;
}

function SheetTitle({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>) {
  return (
    <DialogPrimitive.Title
      className={cn('text-sm font-semibold tracking-tight text-content-primary', className)}
      {...props}
    />
  );
}

function SheetDescription({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>) {
  return (
    <DialogPrimitive.Description
      className={cn('text-xs text-content-muted', className)}
      {...props}
    />
  );
}

export {
  Sheet,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
};
