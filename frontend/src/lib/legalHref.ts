export function legalSearchHref(law?: string | null, article?: string | null): string {
  const query = new URLSearchParams();
  if (law?.trim()) query.set('law', law.trim());
  if (article?.trim()) query.set('article', article.trim());
  const suffix = query.toString();
  return suffix ? `/legal?${suffix}` : '/legal';
}
