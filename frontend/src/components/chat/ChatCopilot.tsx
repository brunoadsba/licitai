'use client';

import { useState } from 'react';
import { MessageCircle } from 'lucide-react';
import ChatPanel from '@/components/chat/ChatPanel';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/Sheet';

interface ChatCopilotProps {
  documentId?: string;
  analysisId?: string;
  itemNumber?: string | null;
  /** Nome do documento (ex.: filename_original) */
  documentLabel?: string | null;
  title?: string;
  page?: string;
  classification?: 'publico' | 'interno' | 'sigiloso';
  /** Na análise, fechado por default para não competir com a revisão. */
  defaultOpen?: boolean;
}

/**
 * Assistente sob demanda (FAB). Fechado por default — não compete com a revisão.
 */
export default function ChatCopilot({
  defaultOpen = false,
  documentLabel,
  ...props
}: ChatCopilotProps) {
  const [open, setOpen] = useState(defaultOpen);
  const label =
    documentLabel ??
    (props.title ? props.title.replace(/^Copiloto\s*[—–-]\s*/i, '') : null);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-40 flex h-12 items-center justify-center gap-2 rounded-lg border border-accent-500/40 bg-accent-700 px-4 text-sm font-medium text-white shadow-rim outline-none transition-transform hover:scale-105 focus-visible:ring-2 focus-visible:ring-accent-500/60"
        aria-label="Perguntar ao copiloto"
      >
        <MessageCircle className="h-5 w-5" aria-hidden />
        <span className="hidden sm:inline">Perguntar</span>
      </button>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent
          side="right"
          className="flex h-full w-full flex-col p-0 sm:max-w-md"
          hideClose={false}
        >
          <SheetHeader className="shrink-0">
            <SheetTitle>Copiloto LicitAI</SheetTitle>
            <SheetDescription>Respostas com base no TR e na lei</SheetDescription>
          </SheetHeader>
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <ChatPanel
              {...props}
              documentLabel={label}
              variant="sheet"
              onClose={() => setOpen(false)}
            />
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
