import { describe, expect, it } from 'vitest';
import { hasPlaceholderText } from './placeholderText';

describe('hasPlaceholderText', () => {
  it.each([
    'prazo de X dias',
    'valor de R$ Y',
    '[inserir objeto]',
    '[preencher aqui]',
    'aguardando ___ assinatura',
    'prazo de {meses} meses',
    'a preencher pelo setor',
  ])('detecta %s', (text) => {
    expect(hasPlaceholderText(text)).toBe(true);
  });

  it.each([
    'prazo de 30 dias',
    'valor de R$ 150.000,00',
    'Objeto definido no item 4.3.2',
    '',
  ])('não acusa %s', (text) => {
    expect(hasPlaceholderText(text)).toBe(false);
  });

  it('nulo é false', () => {
    expect(hasPlaceholderText(null)).toBe(false);
    expect(hasPlaceholderText(undefined)).toBe(false);
  });
});
