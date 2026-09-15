/** API de auditoria TR × Propostas (fornecedores, moldes, matriz) — extraído de `lib/api.ts`. */

import type {
  ComparacaoListResponse,
  ComparacaoResponse,
  ComparacaoStartResponse,
  DryRunResponse,
  Fornecedor,
  MatrizResponse,
  Molde,
  MoldeListResponse,
} from '@/types';
import { fetchAPI, jsonBody } from './client';

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
