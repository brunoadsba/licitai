'use client';

import { useState } from 'react';
import { Check, FileUp, FolderOpen, LoaderCircle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

interface DropZoneProps {
  selectedFile: File | null;
  processing: boolean;
  success: boolean;
  stageLabel: string;
  onFileSelect: (file: File) => void;
  onUpload: () => void;
  onReset: () => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Zona de drop/upload com estados de processamento, sucesso e seleção de arquivo.
 */
export default function DropZone({
  selectedFile,
  processing,
  success,
  stageLabel,
  onFileSelect,
  onUpload,
  onReset,
}: DropZoneProps) {
  const [dragging, setDragging] = useState(false);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onFileSelect(file);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        setDragging(false);
      }}
      onDrop={handleDrop}
      className={cn(
        'glass-card p-8 text-center transition-all duration-200 sm:p-12',
        dragging && 'scale-[1.01] border-accent-500/50 bg-accent-500/[0.06]',
        !dragging && !success && 'hover:border-line-strong',
        success && 'border-green-500/30',
      )}
    >
      {processing ? (
        <div aria-live="polite" className="space-y-6">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-accent-500/25 bg-accent-500/10">
            <LoaderCircle className="h-8 w-8 animate-spin text-accent-400" aria-hidden />
          </div>
          <div>
            <p className="font-medium text-content-primary">{stageLabel}</p>
            <p className="mt-1 text-sm text-content-muted">
              Isso pode levar alguns minutos dependendo do tamanho do documento.
            </p>
          </div>
        </div>
      ) : success ? (
        <div className="space-y-4">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-green-500/25 bg-green-500/10">
            <Check className="h-8 w-8 text-green-400" strokeWidth={2} aria-hidden />
          </div>
          <div>
            <p className="font-medium text-green-400">Documento enviado com sucesso!</p>
            <p className="mt-1 text-sm text-content-muted">Redirecionando para análise…</p>
          </div>
        </div>
      ) : (
        <>
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-line-subtle bg-white/[0.03]">
            <FileUp className="h-8 w-8 text-accent-400" strokeWidth={1.5} aria-hidden />
          </div>

          {selectedFile ? (
            <div className="space-y-4">
              <div className="glass-card inline-flex items-center gap-3 px-5 py-3">
                <span
                  className={`rounded px-2 py-1 text-xs font-semibold uppercase ${
                    selectedFile.name.endsWith('.pdf')
                      ? 'bg-red-500/15 text-red-400'
                      : 'bg-sky-500/15 text-sky-400'
                  }`}
                >
                  {selectedFile.name.split('.').pop()}
                </span>
                <div className="text-left">
                  <p className="max-w-xs truncate text-sm font-medium text-content-primary">
                    {selectedFile.name}
                  </p>
                  <p className="tnum text-xs text-content-subtle">{formatFileSize(selectedFile.size)}</p>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-3">
                <Button onClick={onUpload}>
                  <FileUp className="h-4 w-4" aria-hidden />
                  Enviar e Analisar
                </Button>
                <Button onClick={onReset} variant="secondary">
                  Cancelar
                </Button>
              </div>
            </div>
          ) : (
            <>
              <p className="mb-2 font-medium text-content-secondary">
                Arraste o arquivo aqui ou clique para selecionar
              </p>
              <p className="tnum mb-6 text-sm text-content-subtle">
                Formatos aceitos: PDF, DOCX · Máximo: 50MB
              </p>
              <label className="btn-secondary cursor-pointer">
                <FolderOpen className="h-4 w-4" aria-hidden />
                Selecionar Arquivo
                <input
                  type="file"
                  accept=".pdf,.docx"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) onFileSelect(file);
                  }}
                  className="hidden"
                />
              </label>
            </>
          )}
        </>
      )}
    </div>
  );
}
