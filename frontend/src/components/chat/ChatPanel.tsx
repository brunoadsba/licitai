'use client';

import { useEffect, useRef } from 'react';
import { useChat } from '@/hooks/useChat';
import { getErrorMessage } from '@/lib/errors';
import AlertBanner from '@/components/ui/AlertBanner';
import ChatMessageView from './ChatMessage';
import ChatInput from './ChatInput';

interface ChatPanelProps {
  documentId?: string;
  analysisId?: string;
  itemNumber?: string | null;
  title?: string;
  page?: string;
}

export default function ChatPanel({
  documentId,
  analysisId,
  itemNumber,
  title,
  page,
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

  return (
    <div className="glass-card flex flex-col" style={{ height: 'calc(100vh - 340px)', minHeight: 320 }}>
      {/* Cabeçalho */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.06]">
        <div className="relative flex items-center justify-center">
          <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse absolute opacity-75" />
          <div className="w-2.5 h-2.5 rounded-full bg-cyan-500" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <svg className="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
            </svg>
            Copiloto LicitAI
          </h3>
          <p className="text-[11px] text-gray-500">
            Assistente consultivo com citação de fontes
          </p>
        </div>
        <span className="badge badge-info text-[9px] ml-auto">beta</span>
      </div>

      {/* Mensagens */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {loading ? (
          <div className="space-y-2">
            <div className="skeleton h-12 w-2/3" />
            <div className="skeleton h-12 w-1/2" />
          </div>
        ) : !enabled ? (
          <div className="text-center py-8">
            <p className="text-sm text-gray-400">
              {error || 'O Copiloto não está disponível.'}
            </p>
          </div>
        ) : !hasMessages ? (
          <div className="text-center py-8">
            <svg className="w-12 h-12 mx-auto mb-3 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
            </svg>
            <p className="text-sm text-gray-300 font-medium">
              Olá! Sou o Copiloto LicitAI.
            </p>
            <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
              Posso responder dúvidas sobre este documento, as análises e a
              legislação citada, sempre apontando as fontes.
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
          <div className="flex justify-start animate-slide-up">
            <div className="bg-surface-900/60 border border-white/10 rounded-2xl px-4 py-3">
              <p className="text-sm text-gray-400 flex items-center gap-2">
                <span className="inline-block w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                Consultando fontes jurídicas...
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
                className="text-red-400/70 hover:text-red-300 text-xs shrink-0"
                title="Fechar"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            }
          >
            {chatError.message}
          </AlertBanner>
        )}
      </div>

      {/* Input */}
      <div className="px-4 pb-4">
        <ChatInput disabled={!enabled || loading} sending={sending} onSend={send} />
      </div>
    </div>
  );
}
