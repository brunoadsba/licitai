'use client';

import { useEffect, useRef } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel = 'Cancelar',
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };

    window.addEventListener('keydown', handleKeyDown);
    // Foco inicial no botão de cancelar (ação segura por padrão)
    const raf = requestAnimationFrame(() => cancelRef.current?.focus());

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      cancelAnimationFrame(raf);
    };
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onCancel}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-message"
        className="glass-card max-w-md w-full p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="confirm-dialog-title" className="text-base font-bold text-white">
          {title}
        </h3>
        <p id="confirm-dialog-message" className="text-sm text-gray-400 leading-relaxed">
          {message}
        </p>
        <div className="flex items-center justify-end gap-3">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="btn-secondary"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`btn-primary ${
              danger
                ? 'bg-red-500/20 text-red-400 border border-red-500/40 shadow-none transition-colors hover:bg-red-500/30'
                : ''
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}