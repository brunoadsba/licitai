/** API do gerador de TR — extraído de `lib/api.ts`. */

import { fetchAPI, jsonBody } from './client';

export interface GenerateTRParams {
  tipo_contratacao: string;
  objeto: string;
  justificativa: string;
  valor_estimado?: number;
  prazo_meses: number;
  garantia_exigida: boolean;
  vistoria_exigida: boolean;
  criterio_julgamento: string;
  classification: 'publico' | 'interno' | 'sigiloso';
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
