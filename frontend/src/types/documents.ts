/**
 * Tipos de documentos, itens, revisões e diff — extraído de `types/index.ts`.
 */

export type DocumentStatus = 'uploaded' | 'parsing' | 'parsed' | 'analyzing' | 'completed' | 'error';

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
  tokens_estimated?: number | null;
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
  /** True se o item tem texto de cláusula (não só título/tópico). */
  is_substantive?: boolean;
}

export interface DocumentDetailResponse extends DocumentResponse {
  error_message: string | null;
  items: DocumentItemResponse[];
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
}

export const STATUS_LABELS: Record<DocumentStatus, string> = {
  uploaded: 'Enviado',
  parsing: 'Processando...',
  parsed: 'Pronto para análise',
  analyzing: 'Analisando...',
  completed: 'Concluído',
  error: 'Erro',
};

// ---- Revisões (histórico/versionamento) ----

export interface DocumentRevision {
  id: string;
  document_id: string;
  versao: number;
  rotulo: string;
  descricao: string | null;
  items_snapshot: Record<string, unknown>[];
  created_at: string;
}

export interface DocumentRevisionListResponse {
  revisions: DocumentRevision[];
  total: number;
}

// ---- Diff de versões de TR ----

export interface DiffItemResponse {
  status: string;
  item_number: string;
  titulo: string;
  conteudo_antes: string | null;
  conteudo_depois: string | null;
}

export interface DiffResponse {
  documento_antigo_id: string;
  documento_novo_id: string;
  total: number;
  resumo: Record<string, number>;
  itens: DiffItemResponse[];
}
