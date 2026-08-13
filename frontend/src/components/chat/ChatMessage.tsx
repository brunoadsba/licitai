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
                <span className="badge badge-baixo text-[9px]">Ancorado</span>
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
              <p className="text-[11px] text-yellow-400/70 mt-2 flex items-start gap-1.5">
                <svg className="w-3.5 h-3.5 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
                <span>{message.warning}</span>
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
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.5c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 012.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 00.322-1.672V3a.75.75 0 01.75-.75A2.25 2.25 0 0116.5 4.5c0 1.152-.26 2.243-.723 3.218-.266.558.107 1.282.725 1.282h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 01-2.649 7.521c-.388.482-.987.729-1.605.729H13.48c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 00-1.423-.23H5.904M14.25 9h2.25M5.904 18.75c.083.205.173.405.27.602.197.4-.078.898-.523.898h-.908c-.889 0-1.713-.518-1.972-1.368a12 12 0 01-.521-3.507c0-1.553.295-3.036.831-4.398C3.387 10.203 4.167 9.75 5 9.75h1.053c.472 0 .745.556.5.96a8.958 8.958 0 00-1.302 4.665c0 1.194.232 2.333.654 3.375z" />
                  </svg>
                </button>
                <button
                  onClick={() => onFeedback(message.id, 'down')}
                  className="text-[11px] text-gray-500 hover:text-red-400 transition-colors px-1"
                  title="Resposta não útil"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 15h2.25m8.024-9.473c.212-.03.398.114.398.325 0 .122-.039.24-.11.335L16.5 10.5c.553.275.9.848.9 1.5 0 .652-.347 1.225-.9 1.5l.812 1.613c.071.095.11.213.11.335 0 .211-.186.355-.398.325a8.976 8.976 0 00-6.511-3.012H5.25a.75.75 0 01-.75-.75v-3a.75.75 0 01.75-.75h3.247c2.39 0 4.583-1.026 6.101-2.777.174-.2.418-.333.676-.401zm.268 0h-.008.008zm0 0h-.008.008zM9 12v6.75M4.5 10.5v6.75a.75.75 0 01-.75.75H2.25a.75.75 0 01-.75-.75v-6a.75.75 0 01.75-.75h1.5a.75.75 0 01.75.75z" />
                  </svg>
                </button>
              </div>
            )}
            {feedbackGiven.has(message.id) && (
              <p className="text-[10px] text-gray-600 mt-2 flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                Feedback registrado
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
