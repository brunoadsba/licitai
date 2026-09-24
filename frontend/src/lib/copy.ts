/**
 * Textos da interface do elaborador — PT-BR simples, uma ideia por frase.
 * Sem jargão de sistema. Tratamento: você.
 */

export const copy = {
  nav: {
    painel: 'Painel',
    enviarTr: 'Enviar TR',
    comoUsar: 'Como usar',
    consultarLei: 'Consultar a lei',
    complementos: 'Complementos',
  },
  header: {
    offline: 'Sem conexão com o serviço',
  },
  dashboard: {
    title: 'Seus TRs',
    subtitle: 'Envie um TR, revise o que importa e copie só o que aprovou para o SEI.',
    subtitlePending: (n: number) =>
      n === 1
        ? '1 correção esperando sua decisão.'
        : `${n} correções esperando sua decisão.`,
    emptyTitle: 'Nenhum TR ainda',
    emptyDescription:
      'Envie um Termo de Referência para revisar e copiar o aprovado para o SEI.',
    remove: 'Remover',
    removeTitle: 'Remover documento',
    removeMessage: (name: string) =>
      `Remover "${name}"? Esta ação não pode ser desfeita.`,
    more: 'Mais',
  },
  cta: {
    analisar: 'Analisar',
    acompanhar: 'Acompanhar',
    revisar: 'Revisar',
    abrir: 'Abrir',
    enviarTr: 'Enviar TR',
    copySei: 'Copiar para o SEI',
    copySeiDone: 'Copiado. Cole no SEI',
    copySeiDisabled: 'Aprove ou ajuste pelo menos uma correção',
    copySeiOk: 'Copia só o que você aprovou ou ajustou',
    revisarAgora: 'Revisar agora',
    verTodas: 'Ver todas',
    novaAuditoria: 'Nova auditoria',
  },
  analysis: {
    nextStep: 'Próximo passo:',
    guidedHint: 'Uma correção por vez, as mais graves primeiro.',
    listHint: 'Comece pelas sugestões graves e pelo que falta no TR.',
    guidedDone: 'Você já revisou o que era mais urgente.',
    guidedDoneHint: 'Use "Copiar para o SEI" no topo, ou "Ver todas" para o restante.',
    guidedNone: 'Não há correções urgentes neste TR.',
    guidedNoneHint: 'Abra "Ver todas" para ver o restante.',
    goToSei: 'Ir para o SEI',
    guidedLabel: (i: number, total: number) => `Revisão · ${i} de ${total}`,
  },
  upload: {
    title: 'Enviar TR',
    subtitle:
      'Envie o Termo de Referência. Depois você revisa e copia só o que aprovou para o SEI.',
    classification: 'Classificação',
    publico: 'Público — pode ir para a nuvem',
    interno: 'Interno — pode ir para a nuvem',
    sigiloso: 'Sigiloso — não envia para a nuvem',
    type: 'Tipo de documento',
    tr: 'Termo de Referência',
    proposta: 'Proposta de fornecedor',
  },
  legal: {
    title: 'Consultar a lei',
    loading: 'Carregando a lei…',
    error: 'Não foi possível carregar o texto da lei.',
    empty: 'Comece por um artigo usado com frequência.',
    none: 'Nenhum texto encontrado.',
    open: 'Abrir na lei',
    sourcesTitle: 'Fontes',
    sourcesHint: 'Não é o Planalto. Anote o que entra ou sai.',
    sourceBlurb: {
      'Lei 14.133/2021':
        'Lei de Licitações e Contratos Administrativos. Regra geral da Administração Pública federal.',
      'Lei 13.303/2016':
        'Lei das Estatais. Licitação e contrato da empresa pública — caso da CODEBA.',
      'RILC CODEBA':
        'Regulamento Interno de Licitações e Contratos da CODEBA. Como a empresa aplica a Lei 13.303.',
      tcu: 'Tribunal de Contas da União. Súmulas e acórdãos de controle sobre licitação.',
    },
    tcuWhy:
      'Ainda sem documento oficial conferido. Por isso a análise e o SEI não usam.',
    statusEmUso: 'Em uso',
    statusNaoIngerido: 'Ausente',
    statusQuarentena: 'Fora da análise',
    shortcuts: [
      { law: '14.133', article: 'Art. 6º', label: 'Art. 6º · Lei 14.133' },
      { law: '14.133', article: '', label: 'Lei 14.133' },
      { law: '13.303', article: '', label: 'Lei 13.303' },
    ],
  },
} as const;
