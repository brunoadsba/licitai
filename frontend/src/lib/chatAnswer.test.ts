import { describe, expect, it } from 'vitest';
import { looksLikeId, parseAnswerBlocks, sanitizeChatAnswer } from './chatAnswer';

describe('sanitizeChatAnswer', () => {
  it('remove UUID, source_id e falha de agente', () => {
    const raw =
      'Veja legal:abc-123 em 123e4567-e89b-12d3-a456-426614174000. ' +
      'juridico:failed não aparece. Resposta ok.';
    const out = sanitizeChatAnswer(raw);
    expect(out).not.toContain('123e4567-e89b-12d3-a456-426614174000');
    expect(out).not.toContain('legal:abc-123');
    expect(out).not.toContain('juridico:failed');
    expect(out).toContain('Resposta ok.');
  });

  it('colapsa espaços e quebras', () => {
    expect(sanitizeChatAnswer('a  b\n\n\nc')).toBe('a b\n\nc');
  });
});

describe('parseAnswerBlocks', () => {
  it('parte heading, parágrafo e lista', () => {
    const blocks = parseAnswerBlocks('**Título**\nTexto corrido aqui.\n- um\n- dois');
    expect(blocks).toEqual([
      { kind: 'heading', text: 'Título' },
      { kind: 'paragraph', text: 'Texto corrido aqui.' },
      { kind: 'list', items: ['um', 'dois'] },
    ]);
  });

  it('texto vazio vira zero blocos', () => {
    expect(parseAnswerBlocks('   ')).toEqual([]);
  });
});

describe('looksLikeId', () => {
  it('detecta UUID e source_id', () => {
    expect(looksLikeId('123e4567-e89b-12d3-a456-426614174000')).toBe(true);
    expect(looksLikeId('correction:abc')).toBe(true);
  });

  it('texto normal e nulo dão false', () => {
    expect(looksLikeId('Art. 6º da Lei')).toBe(false);
    expect(looksLikeId(null)).toBe(false);
    expect(looksLikeId(undefined)).toBe(false);
  });
});
