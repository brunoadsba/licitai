'use client';

import { useEffect, useRef } from 'react';
import { useChat } from '@/hooks/useChat';
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
            <span>💬</span> Copiloto LicitAI
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
            <p className="text-2xl mb-2">🤖</p>
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

        {error && !loading && (
          <div className="glass-card border-red-500/20 p-3">
            <p className="text-xs text-red-400 flex items-start gap-2">
              <span>⚠️</span>
              <span>{error}</span>
              <button
                onClick={clearError}
                className="ml-auto text-red-400/70 hover:text-red-300 text-xs"
              >
                ✕
              </button>
            </p>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-4 pb-4">
        <ChatInput disabled={!enabled || loading} sending={sending} onSend={send} />
      </div>
    </div>
  );
}
