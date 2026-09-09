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
  title?: string;
  page?: string;
}

/**
 * Desktop: painel inline. Mobile: FAB + Sheet full-height com focus trap (Radix).
 */
export default function ChatCopilot(props: ChatCopilotProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="hidden lg:block">
        <ChatPanel {...props} variant="docked" />
      </div>

      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-40 flex h-14 w-14 items-center justify-center rounded-full border border-accent-500/40 bg-accent-700 text-white shadow-rim outline-none transition-transform hover:scale-105 focus-visible:ring-2 focus-visible:ring-accent-500/60 lg:hidden"
        aria-label="Abrir Copiloto LicitAI"
      >
        <MessageCircle className="h-6 w-6" aria-hidden />
      </button>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="bottom" className="lg:hidden" hideClose={false}>
          <SheetHeader>
            <SheetTitle>Copiloto LicitAI</SheetTitle>
            <SheetDescription>Assistente consultivo com citação de fontes</SheetDescription>
          </SheetHeader>
          <div className="min-h-0 flex-1 overflow-hidden px-0 pb-0">
            <ChatPanel {...props} variant="sheet" onClose={() => setOpen(false)} />
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
