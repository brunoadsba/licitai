/**
 * Tipos de análise, correções e relatório — extraído de `types/index.ts`.
 */

export type AgentOrigin = 'juridico' | 'tecnico' | 'redacao' | 'estrutural';

export type ReviewStatus = 'pendente' | 'aprovada' | 'rejeitada' | 'ajustada';

export type CorrectionCategory = 'juridica' | 'tecnica' | 'redacao' | 'estrutural';

export type Severity = 'info' | 'baixo' | 'medio' | 'alto' | 'critico';

export type RiskLevel = 'baixo' | 'medio' | 'alto' | 'critico';

export type Importance = 'baixa' | 'media' | 'alta' | 'critica';

export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'completed_with_errors' | 'error';

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
  agent_origin?: AgentOrigin | null;
  review_status?: ReviewStatus;
  review_note?: string | null;
  reviewed_at?: string | null;
  claim_support?: { supported: number; total: number } | null;
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
  analysis_mode?: 'single' | 'multi_agent' | 'economic';
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
  tokens_estimated?: number | null;
  art6_checklist?: Art6ChecklistItem[];
  art6_coverage?: number | null;
  art6_meets_target?: boolean | null;
  analyzed_item_ids?: string[];
  budget_truncated?: boolean;
}

export interface Art6ChecklistItem {
  key: string;
  alinea: string;
  label: string;
  status: 'present' | 'missing' | 'uncertain';
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
  tokens_estimated?: number | null;
  art6_checklist?: Art6ChecklistItem[];
  art6_coverage?: number | null;
  art6_meets_target?: boolean | null;
}

export const CATEGORY_LABELS: Record<CorrectionCategory, string> = {
  juridica: 'Jurídica',
  tecnica: 'Técnica',
  redacao: 'Redação',
  estrutural: 'Estrutura do TR',
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
