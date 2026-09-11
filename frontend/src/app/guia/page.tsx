import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export const metadata = {
  title: 'Guia do usuário | LicitAI',
};

export default function GuiaUsuarioPage() {
  return (
    <article className="animate-fade-in mx-auto max-w-2xl space-y-8">
      <header>
        <Link
          href="/"
          className="mb-3 inline-flex items-center gap-1 text-xs text-content-subtle outline-none hover:text-content-primary focus-visible:ring-2 focus-visible:ring-accent-500/60"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
          Painel
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight text-content-primary">
          Guia do usuário
        </h1>
        <p className="mt-1 text-sm text-content-muted">
          Elaborador de TR · CODEBA. Só vai ao SEI o que você{' '}
          <strong className="font-medium text-content-primary">aprovou</strong> ou{' '}
          <strong className="font-medium text-content-primary">ajustou</strong>.
        </p>
      </header>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-content-primary">Fluxo</h2>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-content-secondary">
          <li>Enviar o TR (PDF ou DOCX, até 50 MB)</li>
          <li>Aguardar a análise</li>
          <li>Revisar (Aprovar / Rejeitar / Ajustar)</li>
          <li>Copiar pacote SEI e colar no processo</li>
        </ol>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-content-primary">Telas</h2>

        <div className="space-y-1.5">
          <h3 className="text-sm font-medium text-content-primary">Painel</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-content-secondary">
            <li>Lista e status de cada TR (Pronto para análise, Concluído, etc.)</li>
            <li>
              <strong className="font-medium text-content-primary">Enviar TR</strong> — novo
              arquivo
            </li>
            <li>
              Por linha:{' '}
              <strong className="font-medium text-content-primary">Analisar</strong>,{' '}
              <strong className="font-medium text-content-primary">Ver resultado</strong> ou{' '}
              <strong className="font-medium text-content-primary">Acompanhar</strong>
            </li>
            <li>
              Com pendências:{' '}
              <strong className="font-medium text-content-primary">Continuar revisão</strong>
            </li>
          </ul>
        </div>

        <div className="space-y-1.5">
          <h3 className="text-sm font-medium text-content-primary">Enviar TR</h3>
          <ol className="list-decimal space-y-1 pl-5 text-sm text-content-secondary">
            <li>Arraste ou escolha o arquivo</li>
            <li>
              Clique em{' '}
              <strong className="font-medium text-content-primary">Enviar e Analisar</strong>
            </li>
            <li>Acompanhe o progresso na tela</li>
          </ol>
          <p className="text-sm text-content-muted">
            Opções avançadas (recolhidas): análise completa, proposta, versões — só se precisar.
          </p>
        </div>

        <div className="space-y-1.5">
          <h3 className="text-sm font-medium text-content-primary">Análise</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-content-secondary">
            <li>
              <strong className="font-medium text-content-primary">Revisar agora</strong> = risco
              alto/crítico + Art. 6º · <strong className="font-medium text-content-primary">Ver todas</strong>{' '}
              = restante
            </li>
            <li>Painel Art. 6º: cobertura estrutural (meta sugerida ≥ 90%)</li>
            <li>
              Sugestões:{' '}
              <strong className="font-medium text-content-primary">Aprovar</strong> /{' '}
              <strong className="font-medium text-content-primary">Rejeitar</strong> /{' '}
              <strong className="font-medium text-content-primary">Ajustar</strong>
            </li>
            <li>
              Com aprovada/ajustada:{' '}
              <strong className="font-medium text-content-primary">Copiar pacote SEI</strong>
            </li>
            <li>
              <strong className="font-medium text-content-primary">Exportar</strong> — HTML, DOCX,
              .md · <strong className="font-medium text-content-primary">Mais</strong> — relatório,
              histórico · <strong className="font-medium text-content-primary">Perguntar</strong>
            </li>
          </ul>
        </div>

        <div className="space-y-1.5">
          <h3 className="text-sm font-medium text-content-primary">Relatório</h3>
          <p className="text-sm text-content-secondary">
            Resumo e Exportar PDF. Pacote SEI continua na Análise.
          </p>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-content-primary">Colar no SEI</h2>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-content-secondary">
          <li>Copiar pacote SEI na Análise</li>
          <li>Colar na minuta/processo</li>
          <li>Conferir o texto antes de concluir</li>
        </ol>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-content-primary">Problemas comuns</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-content-secondary">
          <li>Pacote SEI desabilitado → aprove ou ajuste ao menos uma correção</li>
          <li>Arquivo rejeitado → PDF ou DOCX, até 50 MB</li>
          <li>Sistema indisponível → suporte / equipe do piloto</li>
        </ul>
      </section>

      <p className="text-xs text-content-subtle">
        Tema claro/escuro: interruptor no cabeçalho. Gerar TR e auditoria: Mais ferramentas
        (opcional).
      </p>

      <div className="flex flex-wrap gap-2">
        <Link href="/upload">
          <Button>Enviar TR</Button>
        </Link>
        <Link href="/">
          <Button variant="secondary">Voltar ao Painel</Button>
        </Link>
      </div>
    </article>
  );
}
