'use client';

import { useState } from 'react';

interface ChatInputProps {
  disabled?: boolean;
  sending?: boolean;
  onSend: (content: string) => void;
}

export default function ChatInput({ disabled, sending, onSend }: ChatInputProps) {
  const [value, setValue] = useState('');

  function handleSend() {
    const text = value.trim();
    if (!text || disabled || sending) return;
    onSend(text);
    setValue('');
  }

  return (
    <div className="flex items-end gap-2 pt-3 border-t border-white/[0.06]">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
          }
        }}
        disabled={disabled || sending}
        rows={2}
        placeholder={
          disabled
            ? 'Copiloto indisponível'
            : sending
              ? 'Consultando fontes...'
              : 'Pergunte sobre este documento (ex: “A cláusula de garantia atende à Lei 14.133/21?”)'
        }
        className="flex-1 bg-surface-900/60 border border-white/10 rounded-xl px-3 py-2 text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-primary-500/40 resize-none disabled:opacity-50"
      />
      <button
        onClick={handleSend}
        disabled={disabled || sending || !value.trim()}
        className="btn-primary !px-4 !py-2 text-xs disabled:opacity-40"
        title="Enviar"
      >
        {sending ? (
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
          </svg>
        )}
        Enviar
      </button>
    </div>
  );
}
