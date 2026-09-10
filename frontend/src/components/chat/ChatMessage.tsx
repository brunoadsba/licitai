'use client';

import type { ChatMessage } from '@/types';
import { Check, ThumbsDown, ThumbsUp, TriangleAlert } from 'lucide-react';
import CitationList from './CitationList';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

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
    <div className={cn('animate-slide-up flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-3',
          isUser
            ? 'border border-accent-500/30 bg-accent-600/20 text-content-primary'
            : 'border border-line-strong bg-panel/60 text-content-secondary',
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
        ) : (
          <>
            <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
              {message.grounded && (
                <Badge tone="low" className="text-[9px]">
                  Ancorado
                </Badge>
              )}
              {message.confidence !== null && message.confidence !== undefined && (
                <Badge tone="neutral" className="tnum text-[9px]">
                  {Math.round(message.confidence * 100)}% confiança
                </Badge>
              )}
              {message.provider && (
                <Badge tone="medium" className="text-[9px]">
                  {message.provider}
                </Badge>
              )}
              {message.latency_ms !== null && message.latency_ms !== undefined && (
                <span className="tnum font-mono text-[9px] text-content-subtle">
                  {formatLatency(message.latency_ms)}
                </span>
              )}
            </div>

            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {sending && !message.content ? 'Gerando resposta…' : message.content}
            </p>

            {message.warning && (
              <p className="mt-2 flex items-start gap-1.5 text-[11px] text-yellow-400/70">
                <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                <span>{message.warning}</span>
              </p>
            )}

            <CitationList sources={message.sources} />

            {onFeedback && !feedbackGiven.has(message.id) && message.id > 0 && (
              <div className="mt-2 flex items-center gap-1">
                <button
                  onClick={() => onFeedback(message.id, 'up')}
                  className="rounded-md px-1 py-0.5 text-content-subtle outline-none transition-colors hover:text-green-400 focus-visible:ring-2 focus-visible:ring-accent-500/60"
                  title="Resposta útil"
                  aria-label="Resposta útil"
                >
                  <ThumbsUp className="h-4 w-4" aria-hidden />
                </button>
                <button
                  onClick={() => onFeedback(message.id, 'down')}
                  className="rounded-md px-1 py-0.5 text-content-subtle outline-none transition-colors hover:text-red-400 focus-visible:ring-2 focus-visible:ring-red-500/60"
                  title="Resposta não útil"
                  aria-label="Resposta não útil"
                >
                  <ThumbsDown className="h-4 w-4" aria-hidden />
                </button>
              </div>
            )}
            {feedbackGiven.has(message.id) && (
              <p className="mt-2 flex items-center gap-1 text-[10px] text-content-subtle">
                <Check className="h-3 w-3" aria-hidden />
                Feedback registrado
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
