'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  listMoldes,
  getMolde,
  createMolde,
  updateMolde,
  deleteMolde,
  duplicateMolde,
  validateMoldeDryRun,
  listDocuments,
} from '@/lib/api';
import {
  Molde,
  RegraConfig,
  MoldeConfig,
  AnchorTipo,
  ANCHOR_TIPO_LABELS,
} from '@/types';

const TIPOS: AnchorTipo[] = [
  'numero_inteiro',
  'numero_extenso',
  'booleano',
  'legal',
  'data',
  'percentual',
  'monetario',
  'cnpj',
  'prazo_relativo',
  'cep',
];

function novaRegra(): RegraConfig {
  return {
    id: '',
    rotulo: '',
    tipo: 'numero_inteiro',
    ancora: '',
    unidade: '',
    expectativa: null,
    palavras_chave: [],
    regex: '',
  };
}

export default function MoldesPage() {
  const [moldes, setMoldes] = useState<Molde[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estado do editor
  const [editingId, setEditingId] = useState<string | null>(null);
  const [nome, setNome] = useState('');
  const [descricao, setDescricao] = useState('');
  const [regras, setRegras] = useState<RegraConfig[]>([]);
  const [saving, setSaving] = useState(false);
  const [showJson, setShowJson] = useState(false);

  // Estado do Dry-Run
  const [dryRunModalOpen, setDryRunModalOpen] = useState(false);
  const [dryRunMolde, setDryRunMolde] = useState<Molde | null>(null);
  const [docsList, setDocsList] = useState<any[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const [dryRunLoading, setDryRunLoading] = useState(false);
  const [dryRunResult, setDryRunResult] = useState<any | null>(null);

  const loadMoldes = useCallback(async () => {
    try {
      const data = await listMoldes();
      setMoldes(data.moldes);
    } catch {
      setError('Erro ao carregar moldes. Verifique se o backend está rodando.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMoldes();
  }, [loadMoldes]);

  async function handleDuplicate(id: string) {
    try {
      setError(null);
      await duplicateMolde(id);
      await loadMoldes();
    } catch (err: any) {
      setError(err.message || 'Erro ao duplicar molde.');
    }
  }

  async function openDryRunModal(molde: Molde) {
    try {
      setDryRunMolde(molde);
      setDryRunResult(null);
      setDryRunModalOpen(true);
      const res = await listDocuments();
      const trDocs = res.documents.filter((d: any) => d.document_type === 'tr');
      setDocsList(trDocs);
      if (trDocs.length > 0) {
        setSelectedDocId(trDocs[0].id);
      }
    } catch (err: any) {
      setError('Erro ao carregar documentos para validação.');
    }
  }

  async function executeDryRun() {
    if (!dryRunMolde || !selectedDocId) return;
    try {
      setDryRunLoading(true);
      const res = await validateMoldeDryRun(dryRunMolde.id, selectedDocId);
      setDryRunResult(res);
    } catch (err: any) {
      setError(err.message || 'Erro ao executar validação dry-run.');
    } finally {
      setDryRunLoading(false);
    }
  }

  function startNew() {
    setEditingId(null);
    setNome('');
    setDescricao('');
    setRegras([novaRegra()]);
    setError(null);
  }

  async function startEdit(id: string) {
    try {
      setError(null);
      const molde = await getMolde(id);
      setEditingId(molde.id);
      setNome(molde.nome);
      setDescricao(molde.descricao || '');
      const config = JSON.parse(molde.config_json) as MoldeConfig;
      setRegras(config.regras.map((r) => ({ ...novaRegra(), ...r })));
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar molde.');
    }
  }

  async function handleRemove(id: string) {
    if (!window.confirm('Remover este molde? As comparações existentes serão mantidas.')) {
      return;
    }
    try {
      await deleteMolde(id);
      await loadMoldes();
      if (editingId === id) {
        startNew();
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao remover molde.');
    }
  }

  function updateRegra(index: number, campo: keyof RegraConfig, valor: unknown) {
    setRegras((prev) =>
      prev.map((r, i) => (i === index ? { ...r, [campo]: valor } : r))
    );
  }

  function handlePalavras(index: number, raw: string) {
    const palavras = raw
      .split(',')
      .map((p) => p.trim())
      .filter(Boolean);
    updateRegra(index, 'palavras_chave', palavras);
  }

  function montarConfig(): MoldeConfig {
    return {
      versao: 1,
      regras: regras.map((r) => {
        const base: RegraConfig = { ...r };
        // Limpar campos irrelevantes ao tipo escolhido
        if (base.tipo !== 'booleano') base.palavras_chave = null;
        if (base.tipo !== 'legal') base.regex = null;
        if (!base.ancora?.trim()) base.ancora = null;
        if (!base.unidade?.trim()) base.unidade = null;
        if (base.expectativa === null || base.expectativa === '') base.expectativa = null;
        return base;
      }),
    };
  }

  async function handleSave() {
    if (!nome.trim()) {
      setError('Informe o nome do molde.');
      return;
    }
    const ids = regras.map((r) => r.id.trim());
    if (ids.some((id) => !id)) {
      setError('Todas as regras precisam de um id.');
      return;
    }
    if (new Set(ids).size !== ids.length) {
      setError('Os ids das regras devem ser únicos.');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      const config_json = JSON.stringify(montarConfig(), null, 2);
      if (editingId) {
        await updateMolde(editingId, { nome: nome.trim(), descricao: descricao.trim() || undefined, config_json });
      } else {
        await createMolde({ nome: nome.trim(), descricao: descricao.trim() || undefined, config_json });
      }
      await loadMoldes();
      startNew();
    } catch (err: any) {
      setError(err.message || 'Erro ao salvar molde. Verifique o config_json.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Moldes de Regras</h1>
          <p className="text-gray-400 mt-1 text-sm">
            Editor visual das regras de conformidade para a auditoria TR × Propostas
          </p>
        </div>
        <button onClick={startNew} className="btn-primary">
          Novo Molde
        </button>
      </div>

      {error && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lista de moldes */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Moldes Cadastrados</h2>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="skeleton h-20" />
              ))}
            </div>
          ) : moldes.length === 0 ? (
            <div className="glass-card p-8 text-center">
              <p className="text-gray-500 text-sm">
                Nenhum molde cadastrado. Crie o primeiro.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {moldes.map((m) => (
                <div
                  key={m.id}
                  className={`glass-card-interactive p-4 cursor-pointer transition-all ${
                    editingId === m.id ? 'ring-1 ring-primary-500/50' : ''
                  }`}
                  onClick={() => startEdit(m.id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-200 truncate">
                        {m.nome}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {(() => {
                          try {
                            const c = JSON.parse(m.config_json) as MoldeConfig;
                            return `${c.regras.length} regras`;
                          } catch {
                            return 'config inválido';
                          }
                        })()}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openDryRunModal(m);
                        }}
                        className="p-1 rounded text-gray-400 hover:text-amber-300 hover:bg-amber-500/10 transition-all"
                        title="Testar/Validar contra TR (Dry-Run)"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121 7.5z" />
                        </svg>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDuplicate(m.id);
                        }}
                        className="p-1 rounded text-gray-400 hover:text-primary-300 hover:bg-primary-500/10 transition-all"
                        title="Duplicar molde"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v9.25c0 .621-.504 1.125-1.125 1.125z" />
                        </svg>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemove(m.id);
                        }}
                        className="p-1 rounded text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all"
                        title="Remover molde"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Editor */}
        <div className="lg:col-span-2">
          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold text-white mb-4">
              {editingId ? 'Editar Molde' : 'Novo Molde'}
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
                  Nome do molde
                </label>
                <input
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  placeholder="Ex.: Molde Padrão de TR"
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 uppercase tracking-wider mb-2">
                  Descrição
                </label>
                <input
                  value={descricao}
                  onChange={(e) => setDescricao(e.target.value)}
                  placeholder="Descrição opcional"
                  className="input-field w-full"
                />
              </div>
            </div>

            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-300">
                Regras ({regras.length})
              </h3>
              <button
                onClick={() => setRegras((prev) => [...prev, novaRegra()])}
                className="btn-secondary text-xs"
              >
                + Adicionar Regra
              </button>
            </div>

            {regras.length === 0 ? (
              <div className="glass-card p-8 text-center">
                <p className="text-gray-500 text-sm">
                  Nenhuma regra. Clique em &quot;+ Adicionar Regra&quot;.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {regras.map((regra, index) => (
                  <div key={index} className="glass-card p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500 uppercase tracking-wider">
                        Regra {index + 1}
                      </span>
                      <button
                        onClick={() =>
                          setRegras((prev) => prev.filter((_, i) => i !== index))
                        }
                        className="text-gray-600 hover:text-red-400 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Id</label>
                        <input
                          value={regra.id}
                          onChange={(e) => updateRegra(index, 'id', e.target.value)}
                          placeholder="ex.: vigencia_dias"
                          className="input-field w-full"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Rótulo</label>
                        <input
                          value={regra.rotulo}
                          onChange={(e) => updateRegra(index, 'rotulo', e.target.value)}
                          placeholder="ex.: Vigência mínima"
                          className="input-field w-full"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Tipo de âncora</label>
                        <select
                          value={regra.tipo}
                          onChange={(e) => updateRegra(index, 'tipo', e.target.value as AnchorTipo)}
                          className="input-field w-full"
                        >
                          {TIPOS.map((t) => (
                            <option key={t} value={t}>
                              {ANCHOR_TIPO_LABELS[t]}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">
                          Âncora (texto ou item, ex.: &quot;vigência&quot;)
                        </label>
                        <input
                          value={regra.ancora || ''}
                          onChange={(e) => updateRegra(index, 'ancora', e.target.value)}
                          placeholder="Opcional — busca no documento todo"
                          className="input-field w-full"
                        />
                      </div>

                      {regra.tipo === 'booleano' && (
                        <div className="sm:col-span-2">
                          <label className="block text-xs text-gray-500 mb-1">
                            Palavras-chave (separadas por vírgula)
                          </label>
                          <input
                            value={(regra.palavras_chave || []).join(', ')}
                            onChange={(e) => handlePalavras(index, e.target.value)}
                            placeholder="ex.: garantia, caução"
                            className="input-field w-full"
                          />
                        </div>
                      )}

                      {regra.tipo === 'legal' && (
                        <div className="sm:col-span-2">
                          <label className="block text-xs text-gray-500 mb-1">
                            Regex da referência legal
                          </label>
                          <input
                            value={regra.regex || ''}
                            onChange={(e) => updateRegra(index, 'regex', e.target.value)}
                            placeholder="ex.: 14\.133/2021"
                            className="input-field w-full"
                          />
                        </div>
                      )}

                      {['numero_inteiro', 'numero_extenso'].includes(regra.tipo) && (
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Unidade</label>
                          <input
                            value={regra.unidade || ''}
                            onChange={(e) => updateRegra(index, 'unidade', e.target.value)}
                            placeholder="ex.: dias, meses"
                            className="input-field w-full"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-center gap-3 mt-6">
              <button
                onClick={handleSave}
                disabled={saving || regras.length === 0}
                className="btn-primary"
              >
                {saving ? 'Salvando...' : editingId ? 'Salvar Alterações' : 'Criar Molde'}
              </button>
              <button
                onClick={() => setShowJson((prev) => !prev)}
                className="btn-secondary"
              >
                {showJson ? 'Ocultar JSON' : 'Ver JSON'}
              </button>
            </div>

            {showJson && (
              <pre className="mt-4 p-4 bg-black/40 border border-white/10 rounded-xl text-xs text-green-400 overflow-x-auto whitespace-pre-wrap">
                {JSON.stringify(montarConfig(), null, 2)}
              </pre>
            )}
          </div>
        </div>
      </div>

      {/* Modal de Validação Dry-Run */}
      {dryRunModalOpen && dryRunMolde && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card max-w-2xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <span>🔑</span> Validar Molde contra TR (Dry-Run)
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Molde: <span className="text-primary-300 font-semibold">{dryRunMolde.nome}</span>
                </p>
              </div>
              <button
                onClick={() => setDryRunModalOpen(false)}
                className="text-gray-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            {/* Seletor de TR */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-gray-300">
                Selecione o Termo de Referência para teste:
              </label>
              {docsList.length === 0 ? (
                <p className="text-xs text-amber-400">
                  Nenhum Termo de Referência encontrado. Envie um documento TR na tela de Upload.
                </p>
              ) : (
                <div className="flex items-center gap-3">
                  <select
                    value={selectedDocId}
                    onChange={(e) => setSelectedDocId(e.target.value)}
                    className="input-field flex-1 text-sm bg-surface-900"
                  >
                    {docsList.map((doc) => (
                      <option key={doc.id} value={doc.id}>
                        {doc.filename_original} ({doc.total_items} itens)
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={executeDryRun}
                    disabled={dryRunLoading || !selectedDocId}
                    className="btn-primary shrink-0"
                  >
                    {dryRunLoading ? 'Executando...' : 'Testar Extração'}
                  </button>
                </div>
              )}
            </div>

            {/* Resultados da Validação Dry-Run */}
            {dryRunResult && (
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between bg-surface-900/60 p-3 rounded-lg border border-white/10">
                  <div>
                    <span className="text-xs text-gray-400">Total de regras: </span>
                    <span className="text-xs font-bold text-white">{dryRunResult.total_regras}</span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-400">Correspondências no TR: </span>
                    <span className="text-xs font-bold text-green-400">{dryRunResult.regras_encontradas} / {dryRunResult.total_regras}</span>
                  </div>
                </div>

                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {dryRunResult.resultados.map((r: any) => (
                    <div
                      key={r.regra_id}
                      className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
                        r.encontrado
                          ? 'bg-green-500/10 border-green-500/30 text-green-300'
                          : 'bg-surface-900/40 border-white/5 text-gray-400'
                      }`}
                    >
                      <div>
                        <span className="font-semibold text-gray-200">{r.rotulo}</span>
                        <span className="text-[10px] text-gray-500 ml-2 font-mono">({r.tipo})</span>
                        {r.ancora && (
                          <p className="text-[11px] text-gray-400 mt-0.5">Âncora: "{r.ancora}"</p>
                        )}
                      </div>
                      <div className="text-right">
                        {r.encontrado ? (
                          <span className="font-bold text-green-300 bg-green-500/20 px-2 py-0.5 rounded border border-green-500/30">
                            {r.valor_extraido}
                          </span>
                        ) : (
                          <span className="text-gray-500 italic">Não encontrado</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
