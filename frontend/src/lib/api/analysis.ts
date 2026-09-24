/** API de análises, revisão e exports SEI — extraído de `lib/api.ts`. */

import type {
  AnalysisDetailResponse,
  AnalysisStartResponse,
  CorrectionResponse,
  ReportResponse,
} from '@/types';
import { API_BASE, ApiError, fetchAPI, jsonBody } from './client';

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

export type AuditPackResponse = {
  analysis_id: string;
  document_id: string;
  document_name: string;
  analyzed_at: string | null;
  corpus_version: string | null;
  final_opinion: string | null;
  corrections: Array<{
    id: string;
    item_number: string | null;
    de: string;
    para: string;
    justification: string;
    legal_basis: string | null;
    corpus_version: string | null;
    retrieval_run_id: string | null;
    review_status: string;
    review_note: string | null;
    reviewed_at: string | null;
    grounded: boolean | null;
  }>;
  retrieval_runs: Array<Record<string, unknown>>;
};

export async function getAuditPack(analysisId: string): Promise<AuditPackResponse> {
  return fetchAPI<AuditPackResponse>(`/analysis/${encodeURIComponent(analysisId)}/audit-pack`);
}
