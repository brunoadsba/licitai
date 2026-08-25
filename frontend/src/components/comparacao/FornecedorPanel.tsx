'use client';

import { FileUp, Pencil, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';
import type { Fornecedor } from '@/types';

interface FornecedorPanelProps {
  fornecedores: Fornecedor[];
  editandoId: string | null;
  nome: string;
  cnpj: string;
  email: string;
  propostaFornecedorId: string;
  propostaFile: File | null;
  uploading: boolean;
  setNome: (v: string) => void;
  setCnpj: (v: string) => void;
  setEmail: (v: string) => void;
  setPropostaFornecedorId: (v: string) => void;
  setPropostaFile: (f: File | null) => void;
  onSalvar: () => void;
  onCancelarEdicao: () => void;
  onEditar: (f: Fornecedor) => void;
  onExcluir: (id: string) => void;
  onUpload: () => void;
}

/**
 * Cadastro/edição de fornecedores + upload de proposta.
 */
export default function FornecedorPanel({
  fornecedores,
  editandoId,
  nome,
  cnpj,
  email,
  propostaFornecedorId,
  propostaFile,
  uploading,
  setNome,
  setCnpj,
  setEmail,
  setPropostaFornecedorId,
  setPropostaFile,
  onSalvar,
  onCancelarEdicao,
  onEditar,
  onExcluir,
  onUpload,
}: FornecedorPanelProps) {
  return (
    <div className="space-y-4">
      <div className="glass-card p-4">
        <h3 className="mb-3 text-sm font-semibold text-content-primary">
          {editandoId ? 'Editar Fornecedor' : 'Cadastrar Fornecedor'}
        </h3>
        <div className="space-y-2">
          <input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Nome do fornecedor"
            aria-label="Nome do fornecedor"
            className="input-field w-full"
          />
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <input
              value={cnpj}
              onChange={(e) => setCnpj(e.target.value)}
              placeholder="CNPJ"
              aria-label="CNPJ do fornecedor"
              className="input-field tnum w-full"
            />
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="E-mail"
              aria-label="E-mail do fornecedor"
              type="email"
              className="input-field w-full"
            />
          </div>
          <div className="flex gap-2">
            <Button onClick={onSalvar} variant="secondary" size="sm" className="flex-1">
              {editandoId ? 'Salvar' : 'Cadastrar'}
            </Button>
            {editandoId && (
              <Button onClick={onCancelarEdicao} variant="ghost" size="sm">
                Cancelar
              </Button>
            )}
          </div>
        </div>
        {fornecedores.length > 0 && (
          <div className="mt-3 space-y-1.5">
            {fornecedores.map((f) => (
              <div key={f.id} className="flex items-center justify-between gap-2 text-xs">
                <span className="badge badge-info flex-1 truncate text-[10px]">
                  {f.nome}
                  {f.email ? ` · ${f.email}` : ''}
                </span>
                <div className="flex shrink-0 gap-1">
                  <button
                    onClick={() => onEditar(f)}
                    aria-label={`Editar ${f.nome}`}
                    title="Editar"
                    className="rounded-md p-1.5 text-content-subtle outline-none transition-colors hover:bg-white/[0.06] hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
                  >
                    <Pencil className="h-3.5 w-3.5" aria-hidden />
                  </button>
                  <button
                    onClick={() => onExcluir(f.id)}
                    aria-label={`Excluir ${f.nome}`}
                    title="Excluir"
                    className="rounded-md p-1.5 text-content-subtle outline-none transition-colors hover:bg-red-500/10 hover:text-red-400 focus-visible:ring-2 focus-visible:ring-red-500/60"
                  >
                    <Trash2 className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="glass-card p-4">
        <h3 className="mb-3 text-sm font-semibold text-content-primary">Enviar Proposta</h3>
        <div className="space-y-3">
          <div>
            <span className="mb-2 block text-[11px] uppercase tracking-widest text-content-subtle">
              Fornecedor
            </span>
            <Select value={propostaFornecedorId} onValueChange={setPropostaFornecedorId}>
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
          <div className="flex flex-wrap items-center gap-2">
            <label className="btn-secondary flex-1 cursor-pointer truncate text-center text-xs">
              <FileUp className="h-3.5 w-3.5 shrink-0" aria-hidden />
              <span className="truncate">{propostaFile ? propostaFile.name : 'Selecionar arquivo'}</span>
              <input
                type="file"
                accept=".pdf,.docx"
                className="hidden"
                aria-label="Arquivo da proposta"
                onChange={(e) => setPropostaFile(e.target.files?.[0] || null)}
              />
            </label>
            <Button onClick={onUpload} disabled={!propostaFile || uploading} loading={uploading} size="sm">
              {!uploading && <FileUp className="h-4 w-4" aria-hidden />}
              {uploading ? 'Enviando…' : 'Enviar'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
