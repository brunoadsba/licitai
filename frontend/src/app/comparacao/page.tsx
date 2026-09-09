'use client';

import ConfirmDialog from '@/components/ui/ConfirmDialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import AlertBanner from '@/components/ui/AlertBanner';
import NovaComparacaoForm from '@/components/comparacao/NovaComparacaoForm';
import FornecedorPanel from '@/components/comparacao/FornecedorPanel';
import ComparacaoList from '@/components/comparacao/ComparacaoList';
import { useComparacaoPage } from '@/components/comparacao/useComparacaoPage';

export default function ComparacaoPage() {
  const page = useComparacaoPage();

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-content-primary">
          Auditoria TR × Propostas
        </h1>
        <p className="mt-1 text-sm text-content-muted">
          Compare propostas com o Termo de Referência em etapas separadas
        </p>
      </div>

      {page.error && (
        <AlertBanner variant="error" title="Não foi possível concluir">
          {page.error}
        </AlertBanner>
      )}

      {page.feedbackMsg && (
        <AlertBanner variant="info" title="Feedback enviado">
          {page.feedbackMsg}
        </AlertBanner>
      )}

      <Tabs defaultValue="historico">
        <TabsList aria-label="Seções da auditoria">
          <TabsTrigger value="historico">Histórico</TabsTrigger>
          <TabsTrigger value="nova">Nova auditoria</TabsTrigger>
          <TabsTrigger value="fornecedores">Fornecedores</TabsTrigger>
        </TabsList>

        <TabsContent value="historico">
          <ComparacaoList
            comparacoes={page.comparacoes}
            loading={page.loading}
            sendingFeedbackId={page.sendingFeedbackId}
            feedbackEnviadosIds={page.feedbackEnviadosIds}
            onFeedback={page.handleFeedback}
          />
        </TabsContent>

        <TabsContent value="nova">
          <div className="glass-card p-5 sm:p-6">
            <h2 className="mb-4 text-lg font-semibold tracking-tight text-content-primary">
              Nova Comparação
            </h2>
            <NovaComparacaoForm
              trs={page.trs}
              moldes={page.moldes}
              propostas={page.propostas}
              propostaIds={page.propostaIds}
              submitting={page.submitting}
              onToggleProposta={page.toggleProposta}
              onStart={page.handleStart}
              setTrId={page.setTrId}
              setMoldeId={page.setMoldeId}
            />
          </div>
        </TabsContent>

        <TabsContent value="fornecedores">
          <div className="glass-card p-5 sm:p-6">
            <h2 className="mb-4 text-lg font-semibold tracking-tight text-content-primary">
              Fornecedores e propostas
            </h2>
            <FornecedorPanel
              fornecedores={page.fornecedores}
              editandoId={page.editandoFornecedorId}
              nome={page.novoFornecedor}
              cnpj={page.novoFornecedorCnpj}
              email={page.novoFornecedorEmail}
              propostaFornecedorId={page.propostaFornecedorId}
              propostaFile={page.propostaFile}
              uploading={page.uploading}
              setNome={page.setNovoFornecedor}
              setCnpj={page.setNovoFornecedorCnpj}
              setEmail={page.setNovoFornecedorEmail}
              setPropostaFornecedorId={page.setPropostaFornecedorId}
              setPropostaFile={page.setPropostaFile}
              onSalvar={page.handleCadastrarFornecedor}
              onCancelarEdicao={page.clearFornecedorForm}
              onEditar={page.handleEditarFornecedor}
              onExcluir={(id) => page.setConfirmDeleteId(id)}
              onUpload={page.handleUploadProposta}
            />
          </div>
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={page.confirmDeleteId !== null}
        title="Excluir fornecedor"
        message="Excluir este fornecedor? Esta ação não pode ser desfeita."
        confirmLabel="Excluir"
        danger
        onConfirm={() => {
          if (page.confirmDeleteId) void page.handleExcluirFornecedor(page.confirmDeleteId);
          page.setConfirmDeleteId(null);
        }}
        onCancel={() => page.setConfirmDeleteId(null)}
      />
    </div>
  );
}
