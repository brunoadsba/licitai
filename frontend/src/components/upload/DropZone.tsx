'use client';

import { useState } from 'react';

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
      className={`glass-card p-12 text-center transition-all duration-300 ${
        dragging
          ? 'border-primary-500/50 bg-primary-500/5 scale-[1.02]'
          : 'hover:border-white/10'
      } ${success ? 'border-green-500/30' : ''}`}
    >
      {processing ? (
        /* Processamento com etapas reais */
        <div aria-live="polite" className="space-y-6">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-primary-500/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-primary-400 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          </div>
          <div>
            <p className="text-white font-semibold">{stageLabel}</p>
            <p className="text-gray-500 text-sm mt-1">
              Isso pode levar alguns minutos dependendo do tamanho do documento.
            </p>
          </div>
        </div>
      ) : success ? (
        /* Sucesso */
        <div className="space-y-4">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-green-500/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          </div>
          <div>
            <p className="text-green-400 font-semibold">Documento enviado com sucesso!</p>
            <p className="text-gray-500 text-sm mt-1">Redirecionando para análise...</p>
          </div>
        </div>
      ) : (
        /* Área de drop */
        <>
          <div className="w-16 h-16 mx-auto rounded-2xl bg-primary-500/10 flex items-center justify-center mb-6">
            <svg className="w-8 h-8 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
          </div>

          {selectedFile ? (
            <div className="space-y-4">
              <div className="glass-card inline-flex items-center gap-3 px-5 py-3">
                <span className={`text-xs font-bold uppercase px-2 py-1 rounded ${
                  selectedFile.name.endsWith('.pdf')
                    ? 'bg-red-500/15 text-red-400'
                    : 'bg-blue-500/15 text-blue-400'
                }`}>
                  {selectedFile.name.split('.').pop()}
                </span>
                <div className="text-left">
                  <p className="text-sm text-white font-medium truncate max-w-xs">
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(selectedFile.size)}
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-center gap-3">
                <button onClick={onUpload} className="btn-primary">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                  </svg>
                  Enviar e Analisar
                </button>
                <button onClick={onReset} className="btn-secondary">
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            <>
              <p className="text-gray-300 font-medium mb-2">
                Arraste o arquivo aqui ou clique para selecionar
              </p>
              <p className="text-gray-600 text-sm mb-6">
                Formatos aceitos: PDF, DOCX • Máximo: 50MB
              </p>
              <label className="btn-secondary cursor-pointer">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
                </svg>
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
