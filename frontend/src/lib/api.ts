/**
 * Cliente API — comunicação segura com o backend.
 *
 * Todas as chamadas passam pelo proxy do Next.js (next.config.js rewrites),
 * evitando exposição direta do backend ao client.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}/api/v1${endpoint}`;

  const response = await fetch(url, {
    ...options,
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
    throw new Error(errorMessage);
  }

  // DELETE retorna 204 sem body
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ---- Documentos ----

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  const url = `${API_BASE}/api/v1/documents/upload`;
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorMessage = 'Erro ao enviar documento';
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorMessage;
    } catch {
      // Response body não é JSON
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export async function listDocuments() {
  return fetchAPI<{ documents: any[]; total: number }>('/documents/');
}

export async function getDocument(id: string) {
  return fetchAPI<any>(`/documents/${encodeURIComponent(id)}`);
}

export async function deleteDocument(id: string) {
  return fetchAPI<void>(`/documents/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

// ---- Análises ----

export async function startAnalysis(documentId: string) {
  return fetchAPI<{ analysis_id: string; message: string }>(
    `/analysis/${encodeURIComponent(documentId)}/start`,
    { method: 'POST' }
  );
}

export async function getAnalysis(analysisId: string) {
  return fetchAPI<any>(`/analysis/${encodeURIComponent(analysisId)}`);
}

export async function getReport(analysisId: string) {
  return fetchAPI<any>(`/analysis/${encodeURIComponent(analysisId)}/report`);
}

export async function getDocumentAnalyses(documentId: string) {
  return fetchAPI<any[]>(`/analysis/document/${encodeURIComponent(documentId)}`);
}
