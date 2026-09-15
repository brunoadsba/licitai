export type ReviewSuggestionKind = 'aprovar' | 'rejeitar' | 'ajustar';

export interface ReviewSuggestion {
  correction_id: string;
  suggestion: ReviewSuggestionKind;
  confidence: number;
  reason: string;
  evidence: Record<string, unknown>;
  grounded?: boolean | null;
  legal_valid?: boolean | null;
  has_placeholder?: boolean;
  fail_closed?: boolean;
}
