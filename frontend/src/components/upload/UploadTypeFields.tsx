'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';
import { copy } from '@/lib/copy';

export type DocumentClassification = 'publico' | 'interno' | 'sigiloso';

interface UploadTypeFieldsProps {
  classification: DocumentClassification | '';
  locked?: boolean;
  onClassificationChange: (value: DocumentClassification) => void;
}

export default function UploadTypeFields({
  classification,
  locked = false,
  onClassificationChange,
}: UploadTypeFieldsProps) {
  return (
    <div>
      <span className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
        {copy.upload.classification}
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
          <SelectItem value="publico">{copy.upload.publico}</SelectItem>
          <SelectItem value="interno">{copy.upload.interno}</SelectItem>
          <SelectItem value="sigiloso">{copy.upload.sigiloso}</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
