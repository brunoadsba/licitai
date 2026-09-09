/**
 * Mapeia erros crus do backend para mensagens acionáveis
 * no formato: problema + causa + correção.
 */

export type ErrorContext = 'upload' | 'analysis' | 'documents' | 'chat';

interface FriendlyError {
  title: string;
  message: string;
}

function extractMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return String(err);
}

function matches(text: string, patterns: string[]): boolean {
  const lower = text.toLowerCase();
  return patterns.some((p) => lower.includes(p));
}

export function getErrorMessage(err: unknown, ctx: ErrorContext): FriendlyError {
  const message = extractMessage(err);

  switch (ctx) {
    case 'upload': {
      if (matches(message, ['não permitido', 'tipo de arquivo', 'extensão'])) {
        return {
          title: 'Arquivo inválido',
          message:
            'Não foi possível processar este arquivo. Envie PDF, DOCX ou ODT com até 50 MB. Verifique o arquivo e tente novamente.',
        };
      }
      if (matches(message, ['muito grande', '50 mb', '50mb', 'tamanho'])) {
        return {
          title: 'Arquivo muito grande',
          message:
            'O arquivo excede o limite de 50 MB. Reduza o arquivo ou divida em partes e tente novamente.',
        };
      }
      if (matches(message, ['vazio', 'empty'])) {
        return {
          title: 'Arquivo vazio',
          message:
            'O arquivo enviado está vazio. Selecione um arquivo com conteúdo e tente novamente.',
        };
      }
      return {
        title: 'Falha no envio',
        message:
          'Não foi possível enviar o documento. Verifique a conexão e tente novamente. Se o problema persistir, contate o suporte CODEBA.',
      };
    }

    case 'documents':
      return {
        title: 'Não foi possível carregar',
        message:
          'Não foi possível carregar os documentos. Atualize a página ou tente novamente em instantes.',
      };

    case 'analysis': {
      if (
        matches(message, ['timeout', 'timed out', '429', 'resource_exhausted', 'cota', 'quota', 'rate limit'])
      ) {
        return {
          title: 'Análise demorada',
          message:
            'A análise demorou mais que o esperado. Aguarde alguns minutos e tente novamente.',
        };
      }
      return {
        title: 'Falha na análise',
        message:
          'Não foi possível concluir a análise. Tente novamente; se o problema persistir, contate o suporte CODEBA.',
      };
    }

    case 'chat':
      return {
        title: 'Chat indisponível',
        message:
          'Não foi possível responder no momento. Verifique se o Copiloto está habilitado no backend e tente novamente.',
      };
  }
}