/**
 * Cliente API — comunicação segura com o backend.
 *
 * Todas as chamadas passam pelo proxy do Next.js (next.config.js rewrites),
 * evitando exposição direta do backend ao client.
 */

import type {
  AnalysisDetailResponse,
  AnalysisStartResponse,
  ChatConversation,
  ChatFeedbackResponse,
  ChatHealthResponse,
  ChatMessage,
  ComparacaoListResponse,
  ComparacaoResponse,
  ComparacaoStartResponse,
  DiffResponse,
  DryRunResponse,
  DocumentDetailResponse,
  DocumentListResponse,
  DocumentRevision,
  DocumentRevisionListResponse,
  Fornecedor,
  MatrizResponse,
  Molde,
  MoldeListResponse,
  ReportResponse,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function extractErrorMessage(err: unknown, fallback = 'Erro inesperado.'): string {
  if (err instanceof ApiError || err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  return fallback;
}

type FetchAPIOptions = RequestInit & { timeoutMs?: number };

async function fetchAPI<T>(endpoint: string, options: FetchAPIOptions = {}): Promise<T> {
  const url = `${API_BASE}/api/v1${endpoint}`;
  const { timeoutMs = 30_000, ...requestInit } = options;

  const response = await fetch(url, {
    ...requestInit,
    signal: options.signal ?? AbortSignal.timeout(timeoutMs),
    headers: {
      'Accept': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorMessage = `Erro ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorMessage;
    } catch {
      // Response body não é JSON
    }
    throw new ApiError(errorMessage, response.status);
  }

  // DELETE retorna 204 sem body
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

function jsonBody(data: unknown): BodyInit {
  return JSON.stringify(data);
}

// ---- Documentos ----

export async function uploadDocument(
  file: File,
  options?: { documentType?: 'tr' | 'proposta'; fornecedorId?: string }
): Promise<DocumentDetailResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_type', options?.documentType || 'tr');
  if (options?.fornecedorId) {
    formData.append('fornecedor_id', options.fornecedorId);
  }

  return fetchAPI<DocumentDetailResponse>('/documents/upload', {
    method: 'POST',
    body: formData,
    // Upload inclui parsing síncrono (OCR pode demorar minutos).
    timeoutMs: 300_000,
  });
}

export async function listDocuments(): Promise<DocumentListResponse> {
  return fetchAPI<DocumentListResponse>('/documents/');
}

export async function getDocument(id: string): Promise<DocumentDetailResponse> {
  return fetchAPI<DocumentDetailResponse>(`/documents/${encodeURIComponent(id)}`);
}

export async function deleteDocument(id: string): Promise<void> {
  return fetchAPI<void>(`/documents/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

// ---- Análises ----

export async function startAnalysis(
  documentId: string,
  mode: 'single' | 'multi_agent' = 'multi_agent'
): Promise<AnalysisStartResponse> {
  return fetchAPI<AnalysisStartResponse>(
    `/analysis/${encodeURIComponent(documentId)}/start`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: jsonBody({ mode }),
    }
  );
}

export async function getAnalysis(analysisId: string): Promise<AnalysisDetailResponse> {
  return fetchAPI<AnalysisDetailResponse>(`/analysis/${encodeURIComponent(analysisId)}`);
}

export async function getReport(analysisId: string): Promise<ReportResponse> {
  return fetchAPI<ReportResponse>(`/analysis/${encodeURIComponent(analysisId)}/report`);
}

export async function getDocumentAnalyses(documentId: string): Promise<AnalysisDetailResponse[]> {
  return fetchAPI<AnalysisDetailResponse[]>(`/analysis/document/${encodeURIComponent(documentId)}`);
}

// ---- Auditoria TR × Propostas ----

export async function listFornecedores(): Promise<{ fornecedores: Fornecedor[]; total: number }> {
  return fetchAPI<{ fornecedores: Fornecedor[]; total: number }>('/fornecedores');
}

export async function createFornecedor(data: {
  nome: string;
  cnpj?: string;
  email?: string;
}): Promise<Fornecedor> {
  return fetchAPI<Fornecedor>('/fornecedores', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: jsonBody(data),
  });
}

export async function updateFornecedor(
  fornecedorId: string,
  data: { nome: string; cnpj?: string; email?: string }
): Promise<Fornecedor> {
  return fetchAPI<Fornecedor>(`/fornecedores/${encodeURIComponent(fornecedorId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: jsonBody(data),
  });
}

export async function deleteFornecedor(fornecedorId: string): Promise<void> {
  return fetchAPI<void>(`/fornecedores/${encodeURIComponent(fornecedorId)}`, {
    method: 'DELETE',
  });
}

export async function listMoldes(): Promise<MoldeListResponse> {
  return fetchAPI<MoldeListResponse>('/moldes');
}

export async function getMolde(moldeId: string): Promise<Molde> {
  return fetchAPI<Molde>(`/moldes/${encodeURIComponent(moldeId)}`);
}

export async function createMolde(data: {
  nome: string;
  descricao?: string;
  config_json: string;
}): Promise<Molde> {
  return fetchAPI<Molde>('/moldes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: jsonBody(data),
  });
}

export async function updateMolde(
  moldeId: string,
  data: {
    nome: string;
    descricao?: string;
    config_json: string;
  }
): Promise<Molde> {
  return fetchAPI<Molde>(`/moldes/${encodeURIComponent(moldeId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: jsonBody(data),
  });
}

export async function deleteMolde(moldeId: string): Promise<void> {
  return fetchAPI<void>(`/moldes/${encodeURIComponent(moldeId)}`, {
    method: 'DELETE',
  });
}

export async function startComparacao(data: {
  tr_document_id: string;
  molde_id: string;
  propostas_ids: string[];
}): Promise<ComparacaoStartResponse> {
  return fetchAPI<ComparacaoStartResponse>('/comparison/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: jsonBody(data),
  });
}

export async function listComparacoes(): Promise<ComparacaoListResponse> {
  return fetchAPI<ComparacaoListResponse>('/comparison');
}

export async function getComparacao(comparacaoId: string): Promise<ComparacaoResponse> {
  return fetchAPI<ComparacaoResponse>(`/comparison/${encodeURIComponent(comparacaoId)}`);
}

export async function getMatriz(comparacaoId: string): Promise<MatrizResponse> {
  return fetchAPI<MatrizResponse>(`/comparison/${encodeURIComponent(comparacaoId)}/matrix`);
}

export async function enviarFeedback(comparacaoId: string) {
  return fetchAPI<{
    comparacao_id: string;
    enviados: number;
    falhas: { fornecedor_id: string; nome: string; email?: string; motivo: string }[];
    fornecedores_sem_pendencias: string[];
    fornecedores_sem_email: string[];
  }>(`/comparison/${encodeURIComponent(comparacaoId)}/feedback`, {
    method: 'POST',
  });
}

export async function duplicateMolde(moldeId: string): Promise<Molde> {
  return fetchAPI<Molde>(`/moldes/${encodeURIComponent(moldeId)}/duplicate`, {
    method: 'POST',
  });
}

export async function validateMoldeDryRun(moldeId: string, documentId: string): Promise<DryRunResponse> {
  return fetchAPI<DryRunResponse>(
    `/moldes/${encodeURIComponent(moldeId)}/validate/${encodeURIComponent(documentId)}`,
    { method: 'POST' }
  );
}

export async function diffDocuments(docAntigoId: string, docNovoId: string): Promise<DiffResponse> {
  return fetchAPI<DiffResponse>('/documents/diff', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: jsonBody({
      documento_antigo_id: docAntigoId,
      documento_novo_id: docNovoId,
    }),
  });
}

export async function listRevisions(documentId: string): Promise<DocumentRevisionListResponse> {
  return fetchAPI<DocumentRevisionListResponse>(
    `/documents/${encodeURIComponent(documentId)}/revisions`
  );
}

export async function createRevision(
  documentId: string,
  rotulo: string,
  descricao?: string
): Promise<DocumentRevision> {
  return fetchAPI<DocumentRevision>(`/documents/${encodeURIComponent(documentId)}/revisions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: jsonBody({ rotulo, descricao }),
  });
}

export async function getRevision(documentId: string, versao: number): Promise<DocumentRevision> {
  return fetchAPI<DocumentRevision>(
    `/documents/${encodeURIComponent(documentId)}/revisions/${versao}`
  );
}

export async function restoreRevision(
  documentId: string,
  versao: number
): Promise<DocumentDetailResponse> {
  return fetchAPI<DocumentDetailResponse>(
    `/documents/${encodeURIComponent(documentId)}/revisions/${versao}/restore`,
    { method: 'POST' }
  );
}

export interface GenerateTRParams {
  tipo_contratacao: string;
  objeto: string;
  justificativa: string;
  valor_estimado?: number;
  prazo_meses: number;
  garantia_exigida: boolean;
  vistoria_exigida: boolean;
  criterio_julgamento: string;
}

export interface GenerateTRResult {
  document_id: string;
  filename_original: string;
  tipo_contratacao: string;
  total_itens: number;
  html_completo: string;
  itens: { item_number: string; title: string; content: string }[];
}

export async function generateTR(params: GenerateTRParams): Promise<GenerateTRResult> {
  return fetchAPI<GenerateTRResult>('/generator/tr', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: jsonBody(params),
    timeoutMs: 300_000,
  });
}

// ---- Copiloto (Chat Consultivo) ----

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

export async function listChatConversations(limit = 50, offset = 0): Promise<ChatConversation[]> {
  return fetchAPI<ChatConversation[]>(`/chat/conversations?limit=${limit}&offset=${offset}`);
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
