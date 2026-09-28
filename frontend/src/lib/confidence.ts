/** Fonte única dos números da página /confianca. Atualizar a cada medição. */

export interface ConfidenceBlock {
  label: string;
  value: string;
  source: string;
  sourceHref?: string;
  lastUpdated: string;
  status: 'medido' | 'harness' | 'ausente' | 'texto';
}

export const CONFIDENCE_UPDATED = '2026-09-28';

export function isStale(lastUpdated: string, now = new Date()): boolean {
  const t = new Date(lastUpdated).getTime();
  if (Number.isNaN(t)) return true;
  return (now.getTime() - t) / 86_400_000 > 30;
}

export function formatDateBR(iso: string): string {
  const t = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(t.getTime())) return iso;
  return t.toLocaleDateString('pt-BR');
}

export const CONFIDENCE_BLOCKS: ConfidenceBlock[] = [
  {
    label: 'Precisão (não inventa problema)',
    value: 'Ainda não medida no golden v2',
    source: 'docs/ops/recall-tr-real-2026-09.md (sem rota pública — ver no repo)',
    lastUpdated: CONFIDENCE_UPDATED,
    status: 'ausente',
  },
  {
    label: 'Recall em TR real (não deixa passar)',
    value: 'Não medido — Postgres do piloto com zero análises em 28/09',
    source: 'docs/ops/recall-tr-real-2026-09.md (sem rota pública — ver no repo)',
    lastUpdated: CONFIDENCE_UPDATED,
    status: 'ausente',
  },
  {
    label: 'Limites conhecidos',
    value: 'Recall não garantido · cota free pode parar no meio · sigiloso exige modelo local',
    source: 'Doutrina do piloto (não é medição)',
    lastUpdated: CONFIDENCE_UPDATED,
    status: 'texto',
  },
  {
    label: 'Cobertura de testes',
    value: '435 backend · 47 frontend — suíte verde em 28/09/2026',
    source: 'npm run test + pytest',
    lastUpdated: CONFIDENCE_UPDATED,
    status: 'medido',
  },
  {
    label: 'Histórico de medição',
    value: 'Golden v2 (3 TPs + 18 tripwires; 17 pendentes rejeitados 0/17). Harness v1: recall 0,25 (3/12). Sintético Groq R 0,56 — não usar como precisão atual',
    source: 'e2e/golden/real/tr_pabx.json',
    lastUpdated: CONFIDENCE_UPDATED,
    status: 'harness',
  },
];
