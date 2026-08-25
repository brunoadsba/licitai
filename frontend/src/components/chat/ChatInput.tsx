'use client';

import { useState } from 'react';
import { SendHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

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

  const blocked = disabled || sending;

  return (
    <div className="flex items-end gap-2 border-t border-line-subtle pt-3">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
          }
        }}
        disabled={blocked}
        rows={2}
        aria-label="Mensagem para o Copiloto"
        placeholder={
          disabled
            ? 'Copiloto indisponível'
            : sending
              ? 'Consultando fontes…'
              : 'Pergunte sobre este documento (ex: “A cláusula de garantia atende à Lei 14.133/21?”)'
        }
        className={cn(
          'flex-1 resize-none rounded-lg border bg-white/[0.03] px-3 py-2 text-sm',
          'text-content-primary placeholder:text-content-subtle outline-none transition-all duration-150',
          'focus:border-accent-500/45 focus:ring-[3px] focus:ring-accent-500/20',
          'disabled:opacity-50 border-line-strong',
        )}
      />
      <Button onClick={handleSend} disabled={blocked || !value.trim()} loading={sending} size="md" className="shrink-0">
        {!sending && <SendHorizontal className="h-4 w-4" aria-hidden />}
        Enviar
      </Button>
    </div>
  );
}
