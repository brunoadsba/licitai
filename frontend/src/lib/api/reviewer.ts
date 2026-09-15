/** API do revisor-assistente — extraído para manter `lib/api.ts` enxuto. */

import type { ReviewSuggestion } from '@/types/reviewer';
import { fetchAPI } from './client';

export interface ReviewSuggestionsResponse {
  analysis_id: string;
  total: number;
  pending: number;
  suggestions: ReviewSuggestion[];
}

export async function getReviewSuggestions(
  analysisId: string,
  pendingOnly = true,
): Promise<ReviewSuggestionsResponse> {
  const qs = pendingOnly ? '?pending_only=true' : '?pending_only=false';
  return fetchAPI<ReviewSuggestionsResponse>(
    `/analysis/${encodeURIComponent(analysisId)}/review-suggestions${qs}`,
  );
}

export async function getReviewSuggestion(
  analysisId: string,
  correctionId: string,
): Promise<ReviewSuggestion> {
  return fetchAPI<ReviewSuggestion>(
    `/analysis/${encodeURIComponent(analysisId)}/review-suggestions/${encodeURIComponent(correctionId)}`,
  );
}
