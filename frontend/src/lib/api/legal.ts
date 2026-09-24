import { fetchAPI } from './client';

export type LegalProvision = {
  id: string;
  law_number: string;
  law_title: string;
  path: string;
  article: string | null;
  paragraph: string | null;
  inciso: string | null;
  alinea: string | null;
  item: string | null;
  canonical_text: string;
  status: string;
  version_status: string;
  source_url: string | null;
  validity_start: string | null;
  validity_end: string | null;
  ancestors: Array<{ path: string; text: string; status: string }>;
};

export async function getLegalProvisions(params: {
  law_number?: string;
  path?: string;
  article?: string;
  include_historical?: boolean;
}): Promise<LegalProvision[]> {
  const query = new URLSearchParams();
  if (params.law_number) query.set('law_number', params.law_number);
  if (params.path) query.set('path', params.path);
  if (params.article) query.set('article', params.article);
  if (params.include_historical) query.set('include_historical', 'true');
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return fetchAPI<LegalProvision[]>(`/legal/provisions${suffix}`);
}
