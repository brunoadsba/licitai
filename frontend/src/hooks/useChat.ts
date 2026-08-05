'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  chatHealth,
  createChatConversation,
  getChatMessages,
  sendChatFeedback,
  sendChatMessage,
} from '@/lib/api';
import type { ChatMessage } from '@/types';

interface UseChatOptions {
  documentId?: string;
  analysisId?: string;
  itemNumber?: string | null;
  title?: string;
  page?: string;
}

export function useChat(options: UseChatOptions = {}) {
  const [enabled, setEnabled] = useState(true);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedbackGiven, setFeedbackGiven] = useState<Set<number>>(new Set());
  const hasStartedRef = useRef(false);

  const context = {
    page: options.page || 'analysis',
    document_id: options.documentId || undefined,
    analysis_id: options.analysisId || undefined,
    item_number: options.itemNumber || undefined,
  };

  const init = useCallback(async () => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;
    setLoading(true);
    setError(null);
    try {
      const health = await chatHealth();
      setEnabled(health.enabled);
      if (!health.enabled) {
        setError('O Copiloto está desabilitado no momento.');
        return;
      }
      const conversation = await createChatConversation({
        document_id: options.documentId,
        analysis_id: options.analysisId,
        context,
        title: options.title,
      });
      setConversationId(conversation.id);
      const history = await getChatMessages(conversation.id);
      setMessages(history);
    } catch (err: any) {
      setError(err.message || 'Erro ao iniciar o Copiloto.');
      setEnabled(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const send = useCallback(
    async (content: string) => {
      const text = content.trim();
      if (!text || sending || conversationId === null) return;
      setSending(true);
      setError(null);
      const userMessage: ChatMessage = {
        id: -Date.now(),
        conversation_id: conversationId,
        role: 'user',
        content: text,
        sources: [],
        grounded: false,
        confidence: null,
        provider: null,
        model: null,
        latency_ms: null,
        warning: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      try {
        const assistant = await sendChatMessage(conversationId, text);
        setMessages((prev) => [...prev, assistant]);
      } catch (err: any) {
        setError(err.message || 'Erro ao enviar mensagem.');
      } finally {
        setSending(false);
      }
    },
    [sending, conversationId]
  );

  const giveFeedback = useCallback(
    async (messageId: number, rating: 'up' | 'down') => {
      if (feedbackGiven.has(messageId)) return;
      try {
        await sendChatFeedback(messageId, rating);
        setFeedbackGiven((prev) => new Set(prev).add(messageId));
      } catch {
        // feedback é opcional — falhas não bloqueiam o chat
      }
    },
    [feedbackGiven]
  );

  const clearError = useCallback(() => setError(null), []);

  return {
    enabled,
    conversationId,
    messages,
    loading,
    sending,
    error,
    feedbackGiven,
    send,
    giveFeedback,
    clearError,
  };
}
