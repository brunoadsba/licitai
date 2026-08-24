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
        <h3 className="text-sm font-semibold text-gray-300 mb-3">
          {editandoId ? 'Editar Fornecedor' : 'Cadastrar Fornecedor'}
        </h3>
        <div className="space-y-2">
          <input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Nome do fornecedor"
            className="input-field w-full"
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <input
              value={cnpj}
              onChange={(e) => setCnpj(e.target.value)}
              placeholder="CNPJ"
              className="input-field w-full"
            />
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="E-mail"
              type="email"
              className="input-field w-full"
            />
          </div>
          <div className="flex gap-2">
            <button onClick={onSalvar} className="btn-secondary flex-1">
              {editandoId ? 'Salvar' : 'Cadastrar'}
            </button>
            {editandoId && (
              <button onClick={onCancelarEdicao} className="btn-secondary">
                Cancelar
              </button>
            )}
          </div>
        </div>
        {fornecedores.length > 0 && (
          <div className="mt-3 space-y-1.5">
            {fornecedores.map((f) => (
              <div
                key={f.id}
                className="flex items-center justify-between gap-2 text-xs"
              >
                <span className="badge badge-info text-[10px] truncate flex-1">
                  {f.nome}
                  {f.email ? ` • ${f.email}` : ''}
                </span>
                <div className="flex gap-1 shrink-0">
                  <button
                    onClick={() => onEditar(f)}
                    className="btn-secondary text-[10px] px-2 py-1"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => onExcluir(f.id)}
                    className="btn-secondary text-[10px] px-2 py-1 text-red-400"
                  >
                    Excluir
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="glass-card p-4">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">
          Enviar Proposta
        </h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
              Fornecedor
            </label>
            <select
              value={propostaFornecedorId}
              onChange={(e) => setPropostaFornecedorId(e.target.value)}
              className="input-field w-full"
            >
              <option value="">Selecione o fornecedor...</option>
              {fornecedores.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.nome}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="btn-secondary cursor-pointer flex-1 text-center">
              {propostaFile ? propostaFile.name : 'Selecionar arquivo'}
              <input
                type="file"
                accept=".pdf,.docx"
                className="hidden"
                onChange={(e) => setPropostaFile(e.target.files?.[0] || null)}
              />
            </label>
            <button
              onClick={onUpload}
              disabled={!propostaFile || uploading}
              className="btn-primary"
            >
              {uploading ? 'Enviando...' : 'Enviar'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
