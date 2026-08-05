'use client';

import type { ChatMessage } from '@/types';
import CitationList from './CitationList';

interface ChatMessageProps {
  message: ChatMessage;
  sending?: boolean;
  feedbackGiven: Set<number>;
  onFeedback?: (messageId: number, rating: 'up' | 'down') => void;
}

function formatLatency(ms: number | null): string {
  if (ms === null || ms === undefined) return '';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function ChatMessageView({
  message,
  sending,
  feedbackGiven,
  onFeedback,
}: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-slide-up`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-primary-600/25 border border-primary-500/30 text-gray-100'
            : 'bg-surface-900/60 border border-white/10 text-gray-200'
        }`}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap leading-relaxed">
            {message.content}
          </p>
        ) : (
          <>
            <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
              {message.grounded && (
                <span className="badge badge-baixo text-[9px]">📚 Ancorado</span>
              )}
              {message.confidence !== null && message.confidence !== undefined && (
                <span className="badge badge-info text-[9px]">
                  {Math.round(message.confidence * 100)}% confiança
                </span>
              )}
              {message.provider && (
                <span className="badge badge-medio text-[9px]">
                  {message.provider}
                </span>
              )}
              {message.latency_ms !== null && message.latency_ms !== undefined && (
                <span className="text-[9px] text-gray-500 font-mono">
                  {formatLatency(message.latency_ms)}
                </span>
              )}
            </div>

            <p className="text-sm whitespace-pre-wrap leading-relaxed">
              {sending && !message.content ? 'Gerando resposta...' : message.content}
            </p>

            {message.warning && (
              <p className="text-[11px] text-yellow-400/70 mt-2">
                ⚠️ {message.warning}
              </p>
            )}

            <CitationList sources={message.sources} />

            {onFeedback && !feedbackGiven.has(message.id) && message.id > 0 && (
              <div className="flex items-center gap-1 mt-2">
                <button
                  onClick={() => onFeedback(message.id, 'up')}
                  className="text-[11px] text-gray-500 hover:text-green-400 transition-colors px-1"
                  title="Resposta útil"
                >
                  👍
                </button>
                <button
                  onClick={() => onFeedback(message.id, 'down')}
                  className="text-[11px] text-gray-500 hover:text-red-400 transition-colors px-1"
                  title="Resposta não útil"
                >
                  👎
                </button>
              </div>
            )}
            {feedbackGiven.has(message.id) && (
              <p className="text-[10px] text-gray-600 mt-2">Feedback registrado ✓</p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
