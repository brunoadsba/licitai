'use client';

import { useCallback, useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import {
  createMolde,
  deleteMolde,
  duplicateMolde,
  getMolde,
  listMoldes,
  updateMolde,
  extractErrorMessage,
} from '@/lib/api';
import { Molde, MoldeConfig, RegraConfig } from '@/types';
import { Button } from '@/components/ui/Button';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import DryRunModal from '@/components/moldes/DryRunModal';
import MoldeForm from '@/components/moldes/MoldeForm';
import MoldeList from '@/components/moldes/MoldeList';

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

  const [editingId, setEditingId] = useState<string | null>(null);
  const [nome, setNome] = useState('');
  const [descricao, setDescricao] = useState('');
  const [regras, setRegras] = useState<RegraConfig[]>([]);
  const [saving, setSaving] = useState(false);
  const [showJson, setShowJson] = useState(false);

  const [dryRunMolde, setDryRunMolde] = useState<Molde | null>(null);
  const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);

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
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao duplicar molde.'));
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
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao carregar molde.'));
    }
  }

  async function handleRemove(id: string) {
    try {
      await deleteMolde(id);
      await loadMoldes();
      if (editingId === id) {
        startNew();
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao remover molde.'));
    }
  }

  function updateRegra(index: number, campo: keyof RegraConfig, valor: unknown) {
    setRegras((prev) =>
      prev.map((r, i) => (i === index ? { ...r, [campo]: valor } : r))
    );
  }

  function montarConfig(): MoldeConfig {
    return {
      versao: 1,
      regras: regras.map((r) => {
        const base: RegraConfig = { ...r };
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
    } catch (err) {
      setError(extractErrorMessage(err, 'Erro ao salvar molde. Verifique o config_json.'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="animate-fade-in space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-content-primary">
            Moldes de Regras
          </h1>
          <p className="mt-1 text-sm text-content-muted">
            Editor visual das regras de conformidade para a auditoria TR × Propostas
          </p>
        </div>
        <Button onClick={startNew}>
          <Plus className="h-4 w-4" aria-hidden />
          Novo Molde
        </Button>
      </div>

      {error && (
        <div className="glass-card border-red-500/20 p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div>
          <h2 className="mb-4 text-lg font-semibold tracking-tight text-content-primary">
            Moldes Cadastrados
          </h2>
          <MoldeList
            moldes={moldes}
            loading={loading}
            editingId={editingId}
            onSelect={startEdit}
            onDryRun={setDryRunMolde}
            onDuplicate={handleDuplicate}
            onRemove={setConfirmRemoveId}
          />
        </div>

        <div className="lg:col-span-2">
          <MoldeForm
            editingId={editingId}
            nome={nome}
            descricao={descricao}
            regras={regras}
            saving={saving}
            showJson={showJson}
            onNomeChange={setNome}
            onDescricaoChange={setDescricao}
            onAddRegra={() => setRegras((prev) => [...prev, novaRegra()])}
            onRegraChange={updateRegra}
            onRegraRemove={(index) =>
              setRegras((prev) => prev.filter((_, i) => i !== index))
            }
            onSave={handleSave}
            onToggleJson={() => setShowJson((prev) => !prev)}
            montarConfig={montarConfig}
          />
        </div>
      </div>

      {dryRunMolde && (
        <DryRunModal
          molde={dryRunMolde}
          onClose={() => setDryRunMolde(null)}
          onError={setError}
        />
      )}

      <ConfirmDialog
        open={confirmRemoveId !== null}
        title="Remover molde"
        message="Remover este molde? As comparações existentes serão mantidas."
        confirmLabel="Remover"
        danger
        onConfirm={() => {
          if (confirmRemoveId) handleRemove(confirmRemoveId);
          setConfirmRemoveId(null);
        }}
        onCancel={() => setConfirmRemoveId(null)}
      />
    </div>
  );
}
