/**
 * Compacta o texto "original" no card DE→PARA para não repetir
 * a cláusula inteira já exibida no detalhe do item.
 */

export type OriginalDisplay = {
  mode: 'full' | 'snippet' | 'insertion' | 'omit';
  label: string;
  text: string | null;
};

const INSERTION_RE = /^(adicionar|incluir|inserir)\b/i;

function lastSentences(text: string, count: number): string {
  const parts = text
    .split(/(?<=[.!?…])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (parts.length <= count) return text.trim();
  return parts.slice(-count).join(' ');
}

function overlapRatio(a: string, b: string): number {
  const left = a.trim().toLowerCase().slice(0, 120);
  const right = b.trim().toLowerCase();
  if (!left || !right) return 0;
  if (right.startsWith(left.slice(0, Math.min(80, left.length)))) return 0.9;
  const words = left.split(/\s+/).filter(Boolean);
  if (words.length === 0) return 0;
  const hits = words.filter((w) => right.includes(w)).length;
  return hits / words.length;
}

export function formatOriginalForDisplay(
  original: string,
  suggested: string,
): OriginalDisplay {
  const orig = (original || '').trim();
  const sug = (suggested || '').trim();

  if (!orig) {
    return { mode: 'omit', label: 'Sugerido', text: null };
  }

  if (INSERTION_RE.test(sug)) {
    return {
      mode: 'insertion',
      label: 'Inserção ao final do item',
      text: null,
    };
  }

  if (orig.length <= 200) {
    return { mode: 'full', label: 'Original', text: orig };
  }

  // Original longo + sugestão parece continuar/alterar o mesmo parágrafo
  if (orig.length > 280 && overlapRatio(orig, sug) >= 0.45) {
    return {
      mode: 'snippet',
      label: 'Trecho afetado',
      text: lastSentences(orig, 2),
    };
  }

  if (orig.length > 280) {
    return {
      mode: 'snippet',
      label: 'Trecho afetado',
      text: lastSentences(orig, 2),
    };
  }

  return { mode: 'full', label: 'Original', text: orig };
}
