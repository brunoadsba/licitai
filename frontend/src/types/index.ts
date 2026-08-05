/**
 * Tipos TypeScript para a aplicação.
 * Espelham os schemas Pydantic do backend.
 */

export interface DocumentResponse {
  id: string;
  filename_original: string;
  file_type: string;
  file_size_bytes: number;
  document_type: 'tr' | 'proposta';
  fornecedor_id: string | null;
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

export type AgentOrigin = 'juridico' | 'tecnico' | 'redacao' | 'estrutural';

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
  review_status?: 'pendente' | 'aprovada' | 'rejeitada' | 'ajustada';
  review_note?: string | null;
  reviewed_at?: string | null;
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
  analysis_mode?: 'single' | 'multi_agent';
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

// ---- Auditoria TR × Propostas ----

export interface Fornecedor {
  id: string;
  nome: string;
  cnpj: string | null;
  email: string | null;
  created_at: string;
}

export interface FornecedorListResponse {
  fornecedores: Fornecedor[];
  total: number;
}

export interface Molde {
  id: string;
  nome: string;
  descricao: string | null;
  config_json: string;
  created_at: string;
}

export interface RegraConfig {
  id: string;
  rotulo: string;
  tipo: AnchorTipo;
  ancora?: string | null;
  unidade?: string | null;
  expectativa?: number | string | null;
  palavras_chave?: string[] | null;
  regex?: string | null;
}

export interface MoldeConfig {
  versao: number;
  regras: RegraConfig[];
}

export interface MoldeListResponse {
  moldes: Molde[];
  total: number;
}

export interface ComparacaoStartResponse {
  comparacao_id: string;
  message: string;
}

export interface ComparacaoResponse {
  id: string;
  tr_document_id: string;
  molde_id: string;
  status: ComparacaoStatus;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  total_resultados: number;
  fornecedores: Fornecedor[];
}

export interface ComparacaoListResponse {
  comparacoes: ComparacaoResponse[];
  total: number;
}

export interface MatrizCelula {
  fornecedor_id: string;
  status: ConformidadeStatus;
  motivo: string | null;
  valor_tr: string | null;
  valor_proposta: string | null;
}

export interface MatrizLinha {
  regra_id: string;
  rotulo: string;
  celulas: MatrizCelula[];
}

export interface MatrizResponse {
  comparacao_id: string;
  tr_document_id: string;
  status: string;
  regras: string[];
  fornecedores: Fornecedor[];
  linhas: MatrizLinha[];
}

// Enums
export type DocumentStatus = 'uploaded' | 'parsing' | 'parsed' | 'analyzing' | 'completed' | 'error';
export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'error';
export type ComparacaoStatus = 'pending' | 'running' | 'completed' | 'error';
export type ConformidadeStatus = 'ok' | 'falha' | 'atencao';
export type CorrectionCategory = 'juridica' | 'tecnica' | 'redacao' | 'estrutural';
export type Severity = 'info' | 'baixo' | 'medio' | 'alto' | 'critico';
export type RiskLevel = 'baixo' | 'medio' | 'alto' | 'critico';
export type Importance = 'baixa' | 'media' | 'alta' | 'critica';
export type AnchorTipo =
  | 'numero_inteiro'
  | 'numero_extenso'
  | 'booleano'
  | 'legal'
  | 'data'
  | 'percentual'
  | 'monetario'
  | 'cnpj'
  | 'prazo_relativo'
  | 'cep';

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

export const COMPARACAO_STATUS_LABELS: Record<ComparacaoStatus, string> = {
  pending: 'Pendente',
  running: 'Comparando...',
  completed: 'Concluído',
  error: 'Erro',
};

export const CONFORMIDADE_LABELS: Record<ConformidadeStatus, string> = {
  ok: 'OK',
  falha: 'FALHA',
  atencao: 'ATENÇÃO',
};

export const ANCHOR_TIPO_LABELS: Record<AnchorTipo, string> = {
  numero_inteiro: 'Número inteiro',
  numero_extenso: 'Número por extenso',
  booleano: 'Booleano (presença)',
  legal: 'Referência legal (regex)',
  data: 'Data',
  percentual: 'Percentual',
  monetario: 'Valor monetário (R$)',
  cnpj: 'CNPJ',
  prazo_relativo: 'Prazo relativo (ex: 30 dias)',
  cep: 'CEP',
};

// ---- Copiloto (Chat Consultivo) ----

export type ChatCitationType = 'legal' | 'analysis' | 'correction' | 'document_item';

export interface ChatCitation {
  type: ChatCitationType;
  reference: string;
  title: string;
  snippet: string;
}

export interface ChatSuggestedAction {
  action: string;
  description: string;
}

export interface ChatConversation {
  id: number;
  document_id: string | null;
  analysis_id: string | null;
  context_json: Record<string, unknown>;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  sources: ChatCitation[];
  grounded: boolean;
  confidence: number | null;
  provider: string | null;
  model: string | null;
  latency_ms: number | null;
  warning: string | null;
  created_at: string;
}

export interface ChatHealthResponse {
  enabled: boolean;
  require_grounding: boolean;
  top_k_sources: number;
  max_message_length: number;
  force_fake_provider: boolean;
  llm_provider: string;
}

export interface ChatFeedbackResponse {
  message_id: number;
  rating: 'up' | 'down';
  status: string;
}
