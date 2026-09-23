'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { MessageCircle, Sparkles, X } from 'lucide-react';
import { useChat } from '@/hooks/useChat';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import ChatMessageView from './ChatMessage';
import ChatInput from './ChatInput';
import SuggestionChips, { shouldShowSuggestions } from './SuggestionChips';
import { cn } from '@/lib/utils';

interface ChatPanelProps {
  documentId?: string;
  analysisId?: string;
  itemNumber?: string | null;
  /** Nome do arquivo para contexto no header (sem prefixo "Copiloto —") */
  documentLabel?: string | null;
  title?: string;
  page?: string;
  classification?: 'publico' | 'interno' | 'sigiloso';
  variant?: 'docked' | 'sheet';
  onClose?: () => void;
}

export default function ChatPanel({
  documentId,
  analysisId,
  itemNumber,
  documentLabel,
  title,
  page,
  classification,
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
    classification,
  });

  const scrollRef = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState<string | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending, loading]);

  const handleChip = useCallback(
    (text: string) => {
      if (!enabled || loading || sending) {
        setDraft(text);
        return;
      }
      void send(text);
    },
    [enabled, loading, sending, send],
  );

  const hasMessages = messages.length > 0;
  const chatError = error && !loading ? getErrorMessage(error, 'chat') : null;
  const isSheet = variant === 'sheet';
  const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant');
  const showChipsAfterReply =
    !!lastAssistant &&
    shouldShowSuggestions(
      lastAssistant.content,
      lastAssistant.grounded,
      (lastAssistant.sources?.length ?? 0) > 0,
    );

  const contextBits = [
    documentLabel ? truncateLabel(documentLabel, 36) : null,
    itemNumber ? `Item ${itemNumber}` : null,
  ].filter(Boolean);

  return (
    <section
      aria-label="Copiloto LicitAI"
      className={cn(
        'flex min-h-0 flex-1 flex-col',
        isSheet
          ? 'h-full border-0 bg-transparent'
          : 'glass-card h-[calc(100dvh-340px)] min-h-[360px]',
      )}
    >
      {!isSheet && (
        <div className="flex items-start gap-3 border-b border-line-subtle px-4 py-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-accent-500/25 bg-accent-500/10">
            <MessageCircle className="h-4 w-4 text-accent-400" aria-hidden />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-sm font-semibold text-content-primary">Copiloto LicitAI</h2>
            <p className="text-[11px] text-content-subtle">Respostas com base no TR e na lei</p>
            {contextBits.length > 0 && (
              <p className="mt-0.5 truncate text-[11px] text-content-muted">
                {contextBits.join(' · ')}
              </p>
            )}
          </div>
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

      {isSheet && contextBits.length > 0 && (
        <p className="border-b border-line-subtle px-4 py-2 text-[11px] text-content-muted">
          {contextBits.join(' · ')}
        </p>
      )}

      <div
        ref={scrollRef}
        className="flex min-h-0 flex-1 flex-col justify-end overflow-y-auto px-4 py-3"
      >
        <div className="space-y-3">
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
            <div className="py-6">
              <div className="mb-4 text-center">
                <Sparkles className="mx-auto mb-2.5 h-9 w-9 text-content-subtle" strokeWidth={1.25} aria-hidden />
                <p className="text-sm font-medium text-content-primary">Olá! Sou o Copiloto LicitAI.</p>
                <p className="mx-auto mt-1 max-w-sm text-xs text-content-muted">
                  Pergunte sobre este documento e a legislação citada. Escolha uma sugestão para começar:
                </p>
              </div>
              <SuggestionChips onSelect={handleChip} disabled={sending} className="justify-center" />
            </div>
          ) : (
            <>
              {messages.map((m) => (
                <ChatMessageView
                  key={m.id}
                  message={m}
                  feedbackGiven={feedbackGiven}
                  onFeedback={giveFeedback}
                />
              ))}
              {showChipsAfterReply && !sending && (
                <SuggestionChips onSelect={handleChip} disabled={sending} />
              )}
            </>
          )}

          {sending && (
            <div className="animate-slide-up flex justify-start">
              <div className="rounded-2xl rounded-bl-md bg-surface px-3.5 py-2.5">
                <p className="flex items-center gap-2 text-sm text-content-muted">
                  <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-accent-400" />
                  Buscando no documento…
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
      </div>

      <div className="border-t border-line-subtle bg-panel/80 px-4 py-3 backdrop-blur-sm">
        <ChatInput
          disabled={!enabled || loading}
          sending={sending}
          onSend={send}
          draft={draft}
          onDraftConsumed={() => setDraft(null)}
        />
      </div>
    </section>
  );
}

function truncateLabel(label: string, max: number): string {
  const clean = label.replace(/^Copiloto\s*[—–-]\s*/i, '').trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max - 1)}…`;
}
