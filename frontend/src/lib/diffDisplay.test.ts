import { describe, expect, it } from 'vitest';
import { formatOriginalForDisplay } from './diffDisplay';

describe('formatOriginalForDisplay', () => {
  it('original vazio vira omit', () => {
    expect(formatOriginalForDisplay('', 'texto')).toEqual({
      mode: 'omit',
      label: 'Sugerido',
      text: null,
    });
  });

  it('sugestão de inserção vira insertion', () => {
    const out = formatOriginalForDisplay('trecho longo aqui', 'Adicionar parágrafo sobre prazos');
    expect(out.mode).toBe('insertion');
    expect(out.text).toBeNull();
  });

  it('original curto vira full', () => {
    const out = formatOriginalForDisplay('trecho curto', 'trecho ajustado');
    expect(out).toEqual({ mode: 'full', label: 'Original', text: 'trecho curto' });
  });

  it('original longo vira snippet com as 2 últimas frases', () => {
    const orig = `Primeira frase do item. Segunda frase com contexto. Terceira frase final. ${'x '.repeat(200)}`;
    const out = formatOriginalForDisplay(orig, 'ajuste pontual no item');
    expect(out.mode).toBe('snippet');
    expect(out.label).toBe('Trecho afetado');
    expect(out.text).toContain('Terceira frase final.');
  });

  it('faixa 200-280 sem overlap volta full', () => {
    const orig = `${'palavra '.repeat(28)}fim.`;
    expect(orig.length).toBeGreaterThan(200);
    expect(orig.length).toBeLessThanOrEqual(280);
    const out = formatOriginalForDisplay(orig, 'algo totalmente diferente');
    expect(out.mode).toBe('full');
  });
});
