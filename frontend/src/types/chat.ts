/**
 * Tipos do Copiloto (chat consultivo) — extraído de `types/index.ts`.
 */

export type ChatCitationType = 'legal' | 'analysis' | 'correction' | 'document_item';

export interface ChatCitation {
  type: ChatCitationType;
  source_id?: string | null;
  reference: string;
  title: string;
  snippet: string;
  version?: string | null;
  status?: string | null;
  article?: string | null;
  official_url?: string | null;
  page?: string | null;
  is_interpretation?: boolean;
}

export interface ChatSuggestedAction {
  action: string;
  description: string;
}

export interface ChatConversation {
  id: number;
  document_id: string | null;
  analysis_id: string | null;
  context_json: Record<string, unknown>;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  sources: ChatCitation[];
  grounded: boolean;
  confidence: number | null;
  provider: string | null;
  model: string | null;
  latency_ms: number | null;
  warning: string | null;
  created_at: string;
}

export interface ChatHealthResponse {
  enabled: boolean;
  require_grounding: boolean;
  top_k_sources: number;
  max_message_length: number;
  force_fake_provider: boolean;
  llm_provider: string;
}

export interface ChatFeedbackResponse {
  message_id: number;
  rating: 'up' | 'down';
  status: string;
}
