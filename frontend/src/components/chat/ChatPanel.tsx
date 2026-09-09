'use client';

import { useEffect, useRef } from 'react';
import { MessageCircle, Sparkles, X } from 'lucide-react';
import { useChat } from '@/hooks/useChat';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import ChatMessageView from './ChatMessage';
import ChatInput from './ChatInput';
import { cn } from '@/lib/utils';

interface ChatPanelProps {
  documentId?: string;
  analysisId?: string;
  itemNumber?: string | null;
  title?: string;
  page?: string;
  variant?: 'docked' | 'sheet';
  onClose?: () => void;
}

export default function ChatPanel({
  documentId,
  analysisId,
  itemNumber,
  title,
  page,
  variant = 'docked',
  onClose,
}: ChatPanelProps) {
  const {
    enabled,
    messages,
    loading,
    sending,
    error,
    feedbackGiven,
    send,
    giveFeedback,
    clearError,
  } = useChat({
    documentId,
    analysisId,
    itemNumber,
    title,
    page,
  });

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending, loading]);

  const hasMessages = messages.length > 0;
  const chatError = error && !loading ? getErrorMessage(error, 'chat') : null;
  const isSheet = variant === 'sheet';

  return (
    <section
      aria-label="Copiloto LicitAI"
      className={cn(
        'flex flex-col',
        isSheet
          ? 'h-[min(80dvh,640px)] border-0 bg-transparent'
          : 'glass-card h-[calc(100dvh-340px)] min-h-[360px]',
      )}
    >
      {!isSheet && (
        <div className="flex items-center gap-3 border-b border-line-subtle px-4 py-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-accent-500/25 bg-accent-500/10">
            <MessageCircle className="h-4 w-4 text-accent-400" aria-hidden />
          </div>
          <div>
            <h2 className="flex items-center gap-2 text-sm font-semibold text-content-primary">
              Copiloto LicitAI
            </h2>
            <p className="text-[11px] text-content-subtle">
              Assistente consultivo com citação de fontes
            </p>
          </div>
          <span className="badge badge-info ml-auto text-[9px]">beta</span>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1.5 text-content-muted outline-none hover:bg-white/[0.06] focus-visible:ring-2 focus-visible:ring-accent-500/60"
              aria-label="Fechar Copiloto"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          )}
        </div>
      )}

      <div ref={scrollRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {loading ? (
          <div className="space-y-2">
            <div className="skeleton h-12 w-2/3" />
            <div className="skeleton h-12 w-1/2" />
          </div>
        ) : !enabled ? (
          <div className="py-8 text-center">
            <p className="text-sm text-content-muted">{error || 'O Copiloto não está disponível.'}</p>
          </div>
        ) : !hasMessages ? (
          <div className="py-8 text-center">
            <Sparkles className="mx-auto mb-3 h-12 w-12 text-content-subtle" strokeWidth={1.25} aria-hidden />
            <p className="text-sm font-medium text-content-primary">Olá! Sou o Copiloto LicitAI.</p>
            <p className="mx-auto mt-1 max-w-sm text-xs text-content-muted">
              Posso responder dúvidas sobre este documento, as análises e a legislação citada,
              sempre apontando as fontes.
            </p>
          </div>
        ) : (
          messages.map((m) => (
            <ChatMessageView
              key={m.id}
              message={m}
              feedbackGiven={feedbackGiven}
              onFeedback={giveFeedback}
            />
          ))
        )}

        {sending && (
          <div className="animate-slide-up flex justify-start">
            <div className="rounded-2xl border border-line-strong bg-panel/60 px-4 py-3">
              <p className="flex items-center gap-2 text-sm text-content-muted">
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-accent-400" />
                Consultando fontes jurídicas…
              </p>
            </div>
          </div>
        )}

        {chatError && (
          <AlertBanner
            variant="error"
            title={chatError.title}
            action={
              <button
                onClick={clearError}
                className="shrink-0 text-xs text-red-400/70 outline-none hover:text-red-300 focus-visible:ring-2 focus-visible:ring-red-500/60"
                title="Fechar"
                aria-label="Fechar erro"
              >
                <X className="h-4 w-4" aria-hidden />
              </button>
            }
          >
            {chatError.message}
          </AlertBanner>
        )}
      </div>

      <div className="border-t border-line-subtle px-4 py-3">
        <ChatInput disabled={!enabled || loading} sending={sending} onSend={send} />
      </div>
    </section>
  );
}
