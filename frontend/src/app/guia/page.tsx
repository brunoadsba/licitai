import Link from 'next/link';
import { Button } from '@/components/ui/Button';

export const metadata = {
  title: 'Como usar | LicitAI',
};

export default function GuiaUsuarioPage() {
  return (
    <article className="animate-fade-in mx-auto max-w-2xl space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-content-primary">Como usar</h1>
        <p className="mt-1 text-sm text-content-muted">
          Elaborador de TR · CODEBA. Só vai ao SEI o que você{' '}
          <strong className="font-medium text-content-primary">aprovou</strong> ou{' '}
          <strong className="font-medium text-content-primary">ajustou</strong>.
        </p>
      </header>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-content-primary">Fluxo</h2>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-content-secondary">
          <li>Enviar o TR (PDF, DOCX ou ODT, até 50 MB) e escolher a classificação</li>
          <li>Aguardar a análise</li>
          <li>Revisar (Aprovar / Rejeitar / Ajustar)</li>
          <li>Copiar para o SEI e colar no processo</li>
        </ol>
        <p className="text-sm text-content-muted">
          Documento <strong className="font-medium text-content-primary">sigiloso</strong> não
          vai para a nuvem. Sem modelo local, use Público ou Interno no piloto.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-content-primary">Telas</h2>

        <div className="space-y-1.5">
          <h3 className="text-sm font-medium text-content-primary">Painel</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-content-secondary">
            <li>Lista dos seus TRs, com a data e o que fazer agora</li>
            <li>
              <strong className="font-medium text-content-primary">Enviar TR</strong> — novo
              arquivo
            </li>
            <li>
              Por linha:{' '}
              <strong className="font-medium text-content-primary">Analisar</strong>,{' '}
              <strong className="font-medium text-content-primary">Revisar</strong>,{' '}
              <strong className="font-medium text-content-primary">Abrir</strong> ou{' '}
              <strong className="font-medium text-content-primary">Acompanhar</strong>
            </li>
          </ul>
        </div>

        <div className="space-y-1.5">
          <h3 className="text-sm font-medium text-content-primary">Enviar TR</h3>
          <ol className="list-decimal space-y-1 pl-5 text-sm text-content-secondary">
            <li>Arraste ou escolha o arquivo</li>
            <li>
              Selecione a classificação:{' '}
              <strong className="font-medium text-content-primary">Público</strong>,{' '}
              <strong className="font-medium text-content-primary">Interno</strong> ou{' '}
              <strong className="font-medium text-content-primary">Sigiloso</strong>
            </li>
            <li>
              Clique em{' '}
              <strong className="font-medium text-content-primary">Enviar e Analisar</strong>
            </li>
            <li>Acompanhe o progresso na tela</li>
          </ol>
          <p className="text-sm text-content-muted">
            Opções avançadas: só a abrangência da análise (essencial ou completa).
            Proposta vai em Comparações. Versões de TR vão em Complementos.
          </p>
        </div>

        <div className="space-y-1.5">
          <h3 className="text-sm font-medium text-content-primary">Análise</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-content-secondary">
            <li>
              A tela abre em{' '}
              <strong className="font-medium text-content-primary">Revisar agora</strong> — uma
              correção por vez, as mais graves primeiro
            </li>
            <li>
              <strong className="font-medium text-content-primary">Ver todas</strong> mostra o
              restante do TR
            </li>
            <li>
              Em cada sugestão:{' '}
              <strong className="font-medium text-content-primary">Aprovar</strong> /{' '}
              <strong className="font-medium text-content-primary">Rejeitar</strong> /{' '}
              <strong className="font-medium text-content-primary">Ajustar</strong>
            </li>
            <li>
              Com pelo menos uma aprovada ou ajustada:{' '}
              <strong className="font-medium text-content-primary">Copiar para o SEI</strong>
            </li>
          </ul>
        </div>

        <div className="space-y-1.5">
          <h3 className="text-sm font-medium text-content-primary">Relatório</h3>
          <p className="text-sm text-content-secondary">
            Resumo e Exportar PDF. Copiar para o SEI continua na Análise.
          </p>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-content-primary">Colar no SEI</h2>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-content-secondary">
          <li>Copiar para o SEI na Análise</li>
          <li>Colar na minuta/processo</li>
          <li>Conferir o texto antes de concluir</li>
        </ol>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-content-primary">Problemas comuns</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-content-secondary">
          <li>Copiar para o SEI desabilitado → aprove ou ajuste ao menos uma correção</li>
          <li>Arquivo rejeitado → PDF, DOCX ou ODT, até 50 MB</li>
          <li>Sigiloso recusado → sem modelo local, use Público ou Interno</li>
          <li>Sem conexão com o serviço → suporte / equipe do piloto</li>
        </ul>
      </section>

      <p className="text-sm text-content-muted">
        Telas que apoiam o TR:{' '}
        <Link
          href="/complementos"
          className="text-content-primary underline-offset-2 hover:underline"
        >
          Complementos
        </Link>
        .
      </p>

      <div className="flex flex-wrap gap-2">
        <Link href="/upload">
          <Button>Enviar TR</Button>
        </Link>
      </div>
    </article>
  );
}
