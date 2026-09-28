import { describe, expect, it } from 'vitest';
import type { CorrectionResponse, DocumentItemResponse } from '@/types';
import {
  countPendingPriority,
  filterItemsForPriorityMode,
  filterPriorityCorrections,
  isPriorityCorrection,
  itemHasVisibleCorrections,
} from './priorityQueue';

function corr(over: Partial<CorrectionResponse>): CorrectionResponse {
  return {
    id: 'c1',
    document_item_id: 'i1',
    category: 'tecnica',
    severity: 'medio',
    situation: 's',
    problem: 'p',
    risk: 'r',
    original_text: 'o',
    suggested_text: 'n',
    justification: 'j',
    legal_basis: null,
    importance: 'media',
    ...over,
  };
}

function item(id: string): DocumentItemResponse {
  return {
    id,
    item_number: id,
    title: null,
    content: 'conteúdo',
    page_number: 1,
    item_order: 1,
    item_type: 'clausula',
    corrections_count: 0,
  };
}

describe('isPriorityCorrection', () => {
  it('alto e critico são prioritários', () => {
    expect(isPriorityCorrection(corr({ severity: 'alto' }))).toBe(true);
    expect(isPriorityCorrection(corr({ severity: 'critico' }))).toBe(true);
  });

  it('estrutural é prioritário mesmo com severidade baixa', () => {
    expect(isPriorityCorrection(corr({ severity: 'info', category: 'estrutural' }))).toBe(true);
  });

  it('medio/info não-estrutural não é prioritário', () => {
    expect(isPriorityCorrection(corr({ severity: 'medio' }))).toBe(false);
    expect(isPriorityCorrection(corr({ severity: 'baixo', category: 'juridica' }))).toBe(false);
  });
});

describe('filterPriorityCorrections', () => {
  it('modo all devolve tudo', () => {
    const cs = [corr({}), corr({ severity: 'alto' })];
    expect(filterPriorityCorrections(cs, 'all')).toEqual(cs);
  });

  it('modo priority filtra', () => {
    const cs = [corr({}), corr({ severity: 'alto' })];
    expect(filterPriorityCorrections(cs, 'priority')).toHaveLength(1);
  });
});

describe('countPendingPriority', () => {
  it('conta só prioritário pendente', () => {
    const cs = [
      corr({ severity: 'alto' }),
      corr({ severity: 'alto', review_status: 'aprovada' }),
      corr({ severity: 'baixo' }),
    ];
    expect(countPendingPriority(cs)).toBe(1);
  });

  it('sem review_status conta como pendente', () => {
    expect(countPendingPriority([corr({ severity: 'critico' })])).toBe(1);
  });
});

describe('itens por modo', () => {
  const items = [item('i1'), item('i2')];
  const cs = [corr({ document_item_id: 'i1', severity: 'alto' })];

  it('itemHasVisibleCorrections respeita o item', () => {
    expect(itemHasVisibleCorrections('i1', cs, 'priority')).toBe(true);
    expect(itemHasVisibleCorrections('i2', cs, 'priority')).toBe(false);
  });

  it('filterItemsForPriorityMode volta tudo se nenhum tem achado', () => {
    expect(filterItemsForPriorityMode(items, [], 'priority')).toEqual(items);
  });

  it('filtra itens sem achado prioritário', () => {
    expect(filterItemsForPriorityMode(items, cs, 'priority')).toEqual([items[0]]);
  });
});
