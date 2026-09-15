/** API de documentos, diff de versões e revisões — extraído de `lib/api.ts`. */

import type {
  DiffResponse,
  DocumentDetailResponse,
  DocumentListResponse,
  DocumentResponse,
  DocumentRevision,
  DocumentRevisionListResponse,
} from '@/types';
import { fetchAPI, jsonBody } from './client';

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
