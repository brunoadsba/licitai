'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';
import type { Fornecedor } from '@/types';

export type DocumentClassification = 'publico' | 'interno' | 'sigiloso';

interface UploadTypeFieldsProps {
  documentType: 'tr' | 'proposta';
  fornecedorId: string;
  classification: DocumentClassification | '';
  fornecedores: Fornecedor[];
  locked: boolean;
  onDocumentTypeChange: (value: 'tr' | 'proposta') => void;
  onFornecedorChange: (value: string) => void;
  onClassificationChange: (value: DocumentClassification) => void;
}

export default function UploadTypeFields({
  documentType,
  fornecedorId,
  classification,
  fornecedores,
  locked,
  onDocumentTypeChange,
  onFornecedorChange,
  onClassificationChange,
}: UploadTypeFieldsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div className="md:col-span-2">
        <span className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
          Classificação
        </span>
        <Select
          value={classification || undefined}
          onValueChange={(v) => onClassificationChange(v as DocumentClassification)}
          disabled={locked}
        >
          <SelectTrigger aria-label="Classificação do documento" data-testid="doc-classification">
            <SelectValue placeholder="Selecione a classificação…" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="publico">Público — pode ir para a nuvem</SelectItem>
            <SelectItem value="interno">Interno — pode ir para a nuvem</SelectItem>
            <SelectItem value="sigiloso">Sigiloso — só modelo local</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <span className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
          Tipo de documento
        </span>
        <Select
          value={documentType}
          onValueChange={(v) => onDocumentTypeChange(v as 'tr' | 'proposta')}
          disabled={locked}
        >
          <SelectTrigger aria-label="Tipo de documento" data-testid="doc-type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="tr">Termo de Referência</SelectItem>
            <SelectItem value="proposta">Proposta de fornecedor</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {documentType === 'proposta' && (
        <div>
          <span className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
            Fornecedor
          </span>
          <Select value={fornecedorId} onValueChange={onFornecedorChange} disabled={locked}>
            <SelectTrigger aria-label="Fornecedor da proposta">
              <SelectValue placeholder="Selecione o fornecedor…" />
            </SelectTrigger>
            <SelectContent>
              {fornecedores.map((f) => (
                <SelectItem key={f.id} value={f.id}>
                  {f.nome}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  );
}
