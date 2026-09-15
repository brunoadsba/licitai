/**
 * Tipos de auditoria TR × Propostas (fornecedores, moldes, matriz) — extraído de `types/index.ts`.
 */

export type ComparacaoStatus = 'pending' | 'running' | 'completed' | 'error';

export type ConformidadeStatus = 'ok' | 'falha' | 'atencao';

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

// ---- Dry-Run de moldes ----

export interface DryRunResultado {
  regra_id: string;
  rotulo: string;
  tipo: AnchorTipo;
  ancora: string | null;
  valor_extraido: string | null;
  encontrado: boolean;
}

export interface DryRunResponse {
  molde_id: string;
  molde_nome: string;
  documento_id: string;
  documento_nome: string;
  total_regras: number;
  regras_encontradas: number;
  resultados: DryRunResultado[];
}

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
