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

export async function uploadDocument(
  file: File,
  options?: { documentType?: 'tr' | 'proposta'; fornecedorId?: string }
) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_type', options?.documentType || 'tr');
  if (options?.fornecedorId) {
    formData.append('fornecedor_id', options.fornecedorId);
  }

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

export async function startAnalysis(documentId: string, mode: 'single' | 'multi_agent' = 'multi_agent') {
  return fetchAPI<{ analysis_id: string; message: string }>(
    `/analysis/${encodeURIComponent(documentId)}/start`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    }
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

// ---- Auditoria TR × Propostas ----

export async function listFornecedores() {
  return fetchAPI<{ fornecedores: any[]; total: number }>('/fornecedores');
}

export async function createFornecedor(data: {
  nome: string;
  cnpj?: string;
  email?: string;
}) {
  return fetchAPI<any>('/fornecedores', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function updateFornecedor(
  fornecedorId: string,
  data: { nome: string; cnpj?: string; email?: string }
) {
  return fetchAPI<any>(`/fornecedores/${encodeURIComponent(fornecedorId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function deleteFornecedor(fornecedorId: string) {
  return fetchAPI<void>(`/fornecedores/${encodeURIComponent(fornecedorId)}`, {
    method: 'DELETE',
  });
}

export async function listMoldes() {
  return fetchAPI<{ moldes: any[]; total: number }>('/moldes');
}

export async function getMolde(moldeId: string) {
  return fetchAPI<any>(`/moldes/${encodeURIComponent(moldeId)}`);
}

export async function createMolde(data: {
  nome: string;
  descricao?: string;
  config_json: string;
}) {
  return fetchAPI<any>('/moldes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function updateMolde(
  moldeId: string,
  data: {
    nome: string;
    descricao?: string;
    config_json: string;
  }
) {
  return fetchAPI<any>(`/moldes/${encodeURIComponent(moldeId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function deleteMolde(moldeId: string) {
  return fetchAPI<void>(`/moldes/${encodeURIComponent(moldeId)}`, {
    method: 'DELETE',
  });
}

export async function startComparacao(data: {
  tr_document_id: string;
  molde_id: string;
  propostas_ids: string[];
}) {
  return fetchAPI<{ comparacao_id: string; message: string }>('/comparison/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function listComparacoes() {
  return fetchAPI<{ comparacoes: any[]; total: number }>('/comparison');
}

export async function getComparacao(comparacaoId: string) {
  return fetchAPI<any>(`/comparison/${encodeURIComponent(comparacaoId)}`);
}

export async function getMatriz(comparacaoId: string) {
  return fetchAPI<any>(`/comparison/${encodeURIComponent(comparacaoId)}/matrix`);
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

export async function duplicateMolde(moldeId: string) {
  return fetchAPI<any>(`/moldes/${encodeURIComponent(moldeId)}/duplicate`, {
    method: 'POST',
  });
}

export async function validateMoldeDryRun(moldeId: string, documentId: string) {
  return fetchAPI<any>(`/moldes/${encodeURIComponent(moldeId)}/validate/${encodeURIComponent(documentId)}`, {
    method: 'POST',
  });
}

export async function diffDocuments(docAntigoId: string, docNovoId: string) {
  return fetchAPI<any>('/documents/diff', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      documento_antigo_id: docAntigoId,
      documento_novo_id: docNovoId,
    }),
  });
}
