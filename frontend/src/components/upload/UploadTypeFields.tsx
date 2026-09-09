'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';
import type { Fornecedor } from '@/types';

interface UploadTypeFieldsProps {
  documentType: 'tr' | 'proposta';
  fornecedorId: string;
  fornecedores: Fornecedor[];
  locked: boolean;
  onDocumentTypeChange: (value: 'tr' | 'proposta') => void;
  onFornecedorChange: (value: string) => void;
}

export default function UploadTypeFields({
  documentType,
  fornecedorId,
  fornecedores,
  locked,
  onDocumentTypeChange,
  onFornecedorChange,
}: UploadTypeFieldsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div>
        <span className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
          Tipo de documento
        </span>
        <Select
          value={documentType}
          onValueChange={(v) => onDocumentTypeChange(v as 'tr' | 'proposta')}
          disabled={locked}
        >
          <SelectTrigger aria-label="Tipo de documento">
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
