/** API do Copiloto (chat consultivo) — extraído de `lib/api.ts`. */

import type {
  ChatConversation,
  ChatFeedbackResponse,
  ChatHealthResponse,
  ChatMessage,
} from '@/types';
import { fetchAPI, jsonBody } from './client';

export async function chatHealth(): Promise<ChatHealthResponse> {
  return fetchAPI<ChatHealthResponse>('/chat/health');
}

export async function createChatConversation(data: {
  document_id?: string;
  analysis_id?: string;
  context?: Record<string, unknown>;
  title?: string;
}): Promise<ChatConversation> {
  return fetchAPI<ChatConversation>('/chat/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: jsonBody(data),
  });
}

export async function listChatConversations(
  limit = 50,
  offset = 0,
  filters?: { documentId?: string; analysisId?: string }
): Promise<ChatConversation[]> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (filters?.documentId) params.set('document_id', filters.documentId);
  if (filters?.analysisId) params.set('analysis_id', filters.analysisId);
  return fetchAPI<ChatConversation[]>(`/chat/conversations?${params.toString()}`);
}

export async function getChatMessages(conversationId: number): Promise<ChatMessage[]> {
  return fetchAPI<ChatMessage[]>(`/chat/conversations/${conversationId}/messages`);
}

export async function sendChatMessage(conversationId: number, content: string): Promise<ChatMessage> {
  return fetchAPI<ChatMessage>(`/chat/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: jsonBody({ content }),
    timeoutMs: 120_000,
  });
}

export async function sendChatFeedback(
  messageId: number,
  rating: 'up' | 'down',
  comment?: string
): Promise<ChatFeedbackResponse> {
  return fetchAPI<ChatFeedbackResponse>(`/chat/messages/${messageId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: jsonBody({ rating, comment }),
  });
}
