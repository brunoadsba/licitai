'use client';

import { useState } from 'react';
import { MessageCircle } from 'lucide-react';
import ChatPanel from '@/components/chat/ChatPanel';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog';

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
 * Assistente sob demanda. Abre centralizado, ocupando a maior parte da tela.
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

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          className="flex h-[min(92dvh,860px)] max-h-[92dvh] w-[min(96vw,1100px)] max-w-[1100px] flex-col overflow-hidden p-0"
          hideClose={false}
        >
          <DialogHeader className="mb-0 shrink-0 border-b border-line-subtle px-5 py-4 pr-12">
            <DialogTitle>Copiloto LicitAI</DialogTitle>
            <DialogDescription>
              Pergunte sobre o TR. A resposta indica o próximo passo.
            </DialogDescription>
          </DialogHeader>
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <ChatPanel
              {...props}
              documentLabel={label}
              variant="sheet"
              onClose={() => setOpen(false)}
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
