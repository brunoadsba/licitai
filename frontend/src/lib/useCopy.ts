import { useState, useCallback, useRef } from 'react';

/**
 * Hook de cópia para clipboard com feedback temporário ("Copiado!").
 * Compartilha o estado `copiedKey` para múltiplos botões na mesma tela.
 */
export function useCopy() {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const copy = useCallback((text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setCopiedKey(null), 2000);
  }, []);

  const isCopied = useCallback((key: string) => copiedKey === key, [copiedKey]);

  return { copiedKey, copy, isCopied };
}
