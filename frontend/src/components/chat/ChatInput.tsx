'use client';

import { useEffect, useRef, useState } from 'react';
import { SendHorizontal } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  disabled?: boolean;
  sending?: boolean;
  onSend: (content: string) => void;
  /** Preenche o campo (ex.: chip clicado) e foca o textarea */
  draft?: string | null;
  onDraftConsumed?: () => void;
}

export default function ChatInput({
  disabled,
  sending,
  onSend,
  draft,
  onDraftConsumed,
}: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (draft == null || draft === '') return;
    setValue(draft);
    onDraftConsumed?.();
    requestAnimationFrame(() => {
      const el = textareaRef.current;
      if (!el) return;
      el.focus();
      el.setSelectionRange(draft.length, draft.length);
      resize(el);
    });
  }, [draft, onDraftConsumed]);

  function resize(el: HTMLTextAreaElement) {
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }

  function handleSend() {
    const text = value.trim();
    if (!text || disabled || sending) return;
    onSend(text);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }

  const blocked = disabled || sending;

  return (
    <div className="flex items-end gap-2">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          resize(e.target);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
          }
        }}
        disabled={blocked}
        rows={1}
        aria-label="Mensagem para o Copiloto"
        placeholder={
          disabled
            ? 'Copiloto indisponível'
            : sending
              ? 'Buscando no documento…'
              : 'Pergunte sobre este TR…'
        }
        className={cn(
          'max-h-[120px] min-h-[44px] flex-1 resize-none rounded-xl border bg-canvas/50 px-3.5 py-2.5 text-sm leading-snug',
          'text-content-primary placeholder:text-content-subtle outline-none transition-all duration-150',
          'focus:border-accent-500/45 focus:ring-[3px] focus:ring-accent-500/20',
          'disabled:opacity-50 border-line-subtle',
        )}
      />
      <button
        type="button"
        onClick={handleSend}
        disabled={blocked || !value.trim()}
        aria-label="Enviar mensagem"
        title="Enviar"
        className={cn(
          'inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl',
          'bg-accent-600 text-white outline-none transition-colors',
          'hover:bg-accent-500 focus-visible:ring-2 focus-visible:ring-accent-500/60',
          'disabled:cursor-not-allowed disabled:opacity-40',
        )}
      >
        {sending ? (
          <span className="h-4 w-4 animate-pulse rounded-full bg-white/80" aria-hidden />
        ) : (
          <SendHorizontal className="h-4 w-4" aria-hidden />
        )}
      </button>
    </div>
  );
}
