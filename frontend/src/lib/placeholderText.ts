/**
 * Detecta placeholders óbvios em texto sugerido pela IA
 * (ex.: X, Y, Z, [inserir], ___) que não devem ir direto ao SEI.
 */
const PLACEHOLDER_RE =
  /\b[XYZ]\b|\[inserir[^\]]*\]|\[preencher[^\]]*\]|___+|\{[^}]+\}|a preencher|campo a preencher/i;

export function hasPlaceholderText(text: string | null | undefined): boolean {
  if (!text) return false;
  return PLACEHOLDER_RE.test(text);
}
