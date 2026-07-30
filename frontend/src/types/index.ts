/**
 * Tipos TypeScript para a aplicação.
 * Espelham os schemas Pydantic do backend.
 */

export interface DocumentResponse {
  id: string;
  filename_original: string;
  file_type: string;
  file_size_bytes: number;
  total_items: number;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
}

export interface DocumentItemResponse {
  id: string;
  item_number: string;
  title: string | null;
  content: string;
  page_number: number | null;
  item_order: number;
  item_type: string;
  corrections_count: number;
}

export interface DocumentDetailResponse extends DocumentResponse {
  error_message: string | null;
  items: DocumentItemResponse[];
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
}

export interface CorrectionResponse {
  id: string;
  document_item_id: string;
  category: CorrectionCategory;
  severity: Severity;
  situation: string;
  problem: string;
  risk: string;
  original_text: string;
  suggested_text: string;
  justification: string;
  legal_basis: string | null;
  importance: Importance;
}

export interface AnalysisStartResponse {
  analysis_id: string;
  message: string;
}

export interface AnalysisDetailResponse {
  id: string;
  document_id: string;
  status: AnalysisStatus;
  llm_provider: string;
  llm_model: string;
  total_items: number;
  analyzed_items: number;
  score_overall: number | null;
  score_juridical: number | null;
  score_technical: number | null;
  score_writing: number | null;
  score_structural: number | null;
  risk_level: RiskLevel | null;
  final_opinion: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  corrections: CorrectionResponse[];
}

export interface ScoreDetail {
  label: string;
  score: number | null;
  max_score: number;
}

export interface ReportResponse {
  analysis_id: string;
  document_name: string;
  document_id: string;
  status: string;
  scores: ScoreDetail[];
  risk_level: RiskLevel | null;
  total_corrections: number;
  corrections_by_category: Record<string, number>;
  corrections_by_severity: Record<string, number>;
  corrections: CorrectionResponse[];
  final_opinion: string | null;
  analyzed_at: string | null;
}

// Enums
export type DocumentStatus = 'uploaded' | 'parsing' | 'parsed' | 'analyzing' | 'completed' | 'error';
export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'error';
export type CorrectionCategory = 'juridica' | 'tecnica' | 'redacao' | 'estrutural';
export type Severity = 'info' | 'baixo' | 'medio' | 'alto' | 'critico';
export type RiskLevel = 'baixo' | 'medio' | 'alto' | 'critico';
export type Importance = 'baixa' | 'media' | 'alta' | 'critica';

// Labels em Português
export const CATEGORY_LABELS: Record<CorrectionCategory, string> = {
  juridica: 'Jurídica',
  tecnica: 'Técnica',
  redacao: 'Redação',
  estrutural: 'Estrutural',
};

export const SEVERITY_LABELS: Record<Severity, string> = {
  info: 'Informativo',
  baixo: 'Baixo',
  medio: 'Médio',
  alto: 'Alto',
  critico: 'Crítico',
};

export const RISK_LABELS: Record<RiskLevel, string> = {
  baixo: 'Baixo',
  medio: 'Médio',
  alto: 'Alto',
  critico: 'Crítico',
};

export const STATUS_LABELS: Record<DocumentStatus, string> = {
  uploaded: 'Enviado',
  parsing: 'Processando...',
  parsed: 'Pronto para análise',
  analyzing: 'Analisando...',
  completed: 'Concluído',
  error: 'Erro',
};
