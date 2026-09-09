/** Monta mensagem amigável do envio de pendências por e-mail. */
export function formatFeedbackMessage(result: {
  enviados: number;
  falhas: { nome: string }[];
  fornecedores_sem_pendencias: string[];
  fornecedores_sem_email: string[];
}): string {
  let msg = `Pendências enviadas: ${result.enviados} e-mail(s).`;
  if (result.falhas.length > 0) {
    msg += ` Falhas: ${result.falhas.map((f) => f.nome).join(', ')}.`;
  }
  if (result.fornecedores_sem_pendencias.length > 0) {
    msg += ` Sem pendências: ${result.fornecedores_sem_pendencias.join(', ')}.`;
  }
  if (result.fornecedores_sem_email.length > 0) {
    msg += ` Sem e-mail cadastrado: ${result.fornecedores_sem_email.join(', ')}.`;
  }
  return msg;
}
