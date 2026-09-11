/**
 * Cliente API — comunicação segura com o backend.
 *
 * Chamadas do browser passam pelo BFF (`/api/proxy/...`), que encaminha
 * para `/api/v1/...` e injeta `API_TOKEN` server-side. O token nunca vai para o client.
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
  CorrectionResponse,
  DiffResponse,
  DryRunResponse,
  DocumentDetailResponse,
  DocumentListResponse,
  DocumentResponse,
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

type FetchAPIOptions = RequestInit & { timeoutMs?: number; skipCache?: boolean };

const CACHE_TTL_MS = 30_000;
const apiCache = new Map<string, { expiry: number; data: unknown }>();
const inflightRequests = new Map<string, Promise<unknown>>();

function getCacheKey(endpoint: string, options: FetchAPIOptions): string | null {
  const method = (options.method || 'GET').toUpperCase();
  if (method !== 'GET') return null;
  if (options.skipCache) return null;
  if (typeof window === 'undefined') return null;
  return `${method}:${endpoint}`;
}

function invalidateCache(prefix?: string) {
  if (typeof window === 'undefined') return;
  if (!prefix) {
    apiCache.clear();
    return;
  }
  for (const key of Array.from(apiCache.keys())) {
    if (key.includes(prefix)) apiCache.delete(key);
  }
}

export function clearApiCache() {
  apiCache.clear();
  inflightRequests.clear();
}

async function fetchAPI<T>(endpoint: string, options: FetchAPIOptions = {}): Promise<T> {
  const url = `${API_BASE}/api/proxy${endpoint}`;
  const { timeoutMs = 30_000, skipCache: _skipCache, ...requestInit } = options;

  const cacheKey = getCacheKey(endpoint, options);
  if (cacheKey) {
    const cached = apiCache.get(cacheKey);
    if (cached && cached.expiry > Date.now()) {
      return cached.data as T;
    }
    const inflight = inflightRequests.get(cacheKey);
    if (inflight) {
      return inflight as Promise<T>;
    }
  }

  const doFetch = async (): Promise<T> => {
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

    if (response.status === 204) {
      return undefined as T;
    }

    const data = (await response.json()) as T;
    if (cacheKey) {
      apiCache.set(cacheKey, { expiry: Date.now() + CACHE_TTL_MS, data });
    }
    return data;
  };

  if (cacheKey) {
    const promise = doFetch().finally(() => {
      inflightRequests.delete(cacheKey);
    });
    inflightRequests.set(cacheKey, promise as Promise<unknown>);
    return promise;
  }

  const result = await doFetch();
  const method = (options.method || 'GET').toUpperCase();
  if (method !== 'GET') {
    const prefix = endpoint.split('/')[1] || '';
    if (prefix) invalidateCache(prefix);
    else invalidateCache();
  }
  return result
}

function jsonBody(data: unknown): BodyInit {
  return JSON.stringify(data);
}

// ---- Documentos ----

export async function uploadDocument(
  file: File,
  options?: { documentType?: 'tr' | 'proposta'; fornecedorId?: string }
): Promise<DocumentResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_type', options?.documentType || 'tr');
  if (options?.fornecedorId) {
    formData.append('fornecedor_id', options.fornecedorId);
  }

  return fetchAPI<DocumentResponse>('/documents/upload', {
    method: 'POST',
    body: formData,
    // Upload inclui parsing síncrono (OCR pode demorar minutos).
    timeoutMs: 300_000,
  });
}

export async function listDocuments(): Promise<DocumentListResponse> {
  return fetchAPI<DocumentListResponse>('/documents');
}

export async function getDocument(
  id: string,
  options?: { skipCache?: boolean; signal?: AbortSignal }
): Promise<DocumentDetailResponse> {
  return fetchAPI<DocumentDetailResponse>(`/documents/${encodeURIComponent(id)}`, {
    skipCache: options?.skipCache,
    signal: options?.signal,
  });
}

export async function deleteDocument(id: string): Promise<void> {
  return fetchAPI<void>(`/documents/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

// ---- Análises ----

export async function startAnalysis(
  documentId: string,
  mode: 'single' | 'multi_agent' | 'economic' = 'economic'
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

export async function reanalyzePartial(
  analysisId: string
): Promise<AnalysisStartResponse> {
  return fetchAPI<AnalysisStartResponse>(
    `/analysis/${encodeURIComponent(analysisId)}/reanalyze-partial`,
    { method: 'POST' },
  );
}

export type PendingSummaryResponse = {
  total: number;
  items: Array<{
    document_id: string;
    analysis_id: string;
    filename: string;
    pending_priority: number;
    status: string;
  }>;
};

export async function getPendingSummary(): Promise<PendingSummaryResponse> {
  return fetchAPI<PendingSummaryResponse>('/analysis/pending-summary');
}

export type MetricsSnapshot = {
  uptime_seconds: number;
  counters: Record<string, number>;
  gauges: Record<string, number>;
  analysis_duration_avg_seconds: number;
  analysis_duration_count: number;
};

/** Métricas in-memory do backend (rewrite /metrics). */
export async function getMetricsSnapshot(): Promise<MetricsSnapshot> {
  const res = await fetch('/metrics', { cache: 'no-store' });
  if (!res.ok) throw new ApiError('Falha ao obter métricas', res.status);
  return res.json();
}

export async function getAnalysis(
  analysisId: string,
  options?: { skipCache?: boolean; signal?: AbortSignal }
): Promise<AnalysisDetailResponse> {
  return fetchAPI<AnalysisDetailResponse>(`/analysis/${encodeURIComponent(analysisId)}`, {
    skipCache: options?.skipCache,
    signal: options?.signal,
  });
}

export type CorrectionReviewPayload = {
  review_status: 'pendente' | 'aprovada' | 'rejeitada' | 'ajustada';
  review_note?: string | null;
  suggested_text?: string | null;
  justification?: string | null;
};

export async function updateCorrectionReview(
  correctionId: string,
  payload: CorrectionReviewPayload
): Promise<CorrectionResponse> {
  return fetchAPI<CorrectionResponse>(
    `/analysis/corrections/${encodeURIComponent(correctionId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: jsonBody(payload),
    }
  );
}

export async function getReport(analysisId: string): Promise<ReportResponse> {
  return fetchAPI<ReportResponse>(`/analysis/${encodeURIComponent(analysisId)}/report`);
}

export type SeiPackResponse = {
  analysis_id: string;
  document_id: string;
  document_name: string;
  total: number;
  text: string;
  entries: Array<{
    correction_id: string;
    item_number: string;
    title: string | null;
    suggested_text: string;
    justification: string;
    legal_basis: string | null;
    severity: string;
    category: string;
  }>;
};

export async function getSeiPack(analysisId: string): Promise<SeiPackResponse> {
  return fetchAPI<SeiPackResponse>(`/analysis/${encodeURIComponent(analysisId)}/sei-pack`);
}

export type CorrectedHtmlResponse = {
  document_id: string;
  analysis_id: string;
  document_name: string;
  applied_corrections: number;
  skipped_corrections?: Array<{ correction_id: string; reason: string }>;
  html: string;
};

export async function getCorrectedHtml(analysisId: string): Promise<CorrectedHtmlResponse> {
  return fetchAPI<CorrectedHtmlResponse>(
    `/analysis/${encodeURIComponent(analysisId)}/corrected-html`,
  );
}

/** Baixa TR corrigido em .docx via BFF (blob). */
export async function downloadCorrectedDocx(analysisId: string): Promise<{
  filename: string;
  skipped: number;
  applied: number;
}> {
  const url = `${API_BASE}/api/proxy/analysis/${encodeURIComponent(analysisId)}/corrected-docx`;
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) {
    let detail = 'Falha ao baixar DOCX.';
    try {
      const err = await response.json();
      if (err?.detail) detail = typeof err.detail === 'string' ? err.detail : detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, response.status);
  }
  const blob = await response.blob();
  const cd = response.headers.get('Content-Disposition') || '';
  const match = /filename="?([^"]+)"?/i.exec(cd);
  const filename = match?.[1] || `tr-corrigido-${analysisId.slice(0, 8)}.docx`;
  const applied = Number(response.headers.get('X-Applied-Corrections') || '0');
  const skipped = Number(response.headers.get('X-Skipped-Corrections') || '0');
  const objectUrl = URL.createObjectURL(blob);
  const a = window.document.createElement('a');
  a.href = objectUrl;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(objectUrl);
  return { filename, applied, skipped };
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

export async function getComparacao(
  comparacaoId: string,
  options?: { skipCache?: boolean; signal?: AbortSignal }
): Promise<ComparacaoResponse> {
  return fetchAPI<ComparacaoResponse>(`/comparison/${encodeURIComponent(comparacaoId)}`, {
    skipCache: options?.skipCache,
    signal: options?.signal,
  });
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
