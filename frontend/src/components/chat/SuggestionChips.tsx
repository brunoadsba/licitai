'use client';

import { cn } from '@/lib/utils';

/** Perguntas prontas para Solange / elaborador — sem jargão de TI. */
export const CHAT_SUGGESTIONS = [
  'O que falta no Art. 6º neste TR?',
  'Há risco jurídico no objeto da contratação?',
  'Quais correções são mais urgentes?',
] as const;

interface SuggestionChipsProps {
  onSelect: (text: string) => void;
  disabled?: boolean;
  className?: string;
}

export default function SuggestionChips({
  onSelect,
  disabled,
  className,
}: SuggestionChipsProps) {
  return (
    <div className={cn('flex flex-wrap gap-2', className)} role="group" aria-label="Sugestões de pergunta">
      {CHAT_SUGGESTIONS.map((text) => (
        <button
          key={text}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(text)}
          className={cn(
            'rounded-full border border-accent-500/35 bg-accent-500/10 px-3 py-1.5',
            'text-left text-xs font-medium text-accent-700 dark:text-accent-300',
            'outline-none transition-colors hover:bg-accent-500/20',
            'focus-visible:ring-2 focus-visible:ring-accent-500/60',
            'disabled:cursor-not-allowed disabled:opacity-50',
          )}
        >
          {text}
        </button>
      ))}
    </div>
  );
}

/** Indica se a última resposta pede redirecionamento (saudação / fora de escopo / sem fontes). */
export function shouldShowSuggestions(content: string, grounded: boolean, hasSources: boolean): boolean {
  if (grounded || hasSources) return false;
  const lower = content.toLowerCase();
  return (
    lower.includes('olá') ||
    lower.includes('posso ajudar') ||
    lower.includes('reformule') ||
    lower.includes('sugestões') ||
    lower.includes('não encontrei fontes')
  );
}
