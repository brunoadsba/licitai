import { describe, expect, it, vi } from 'vitest';
import { formatDateBR, isStale } from './confidence';

describe('isStale', () => {
  it('mais de 30 dias fica stale', () => {
    expect(isStale('2026-09-28', new Date('2026-10-29T12:00:00'))).toBe(true);
  });

  it('dentro de 30 dias não fica', () => {
    expect(isStale('2026-09-28', new Date('2026-10-01T12:00:00'))).toBe(false);
  });

  it('data inválida fica stale (falha segura)', () => {
    expect(isStale('não-data')).toBe(true);
    expect(isStale('')).toBe(true);
  });
});

describe('formatDateBR', () => {
  it('formata ISO em pt-BR', () => {
    expect(formatDateBR('2026-09-28')).toBe('28/09/2026');
  });

  it('devolve original se inválida', () => {
    expect(formatDateBR('x')).toBe('x');
  });

  it('usa toLocaleDateString', () => {
    const spy = vi.spyOn(Date.prototype, 'toLocaleDateString');
    formatDateBR('2026-09-28');
    expect(spy).toHaveBeenCalledWith('pt-BR');
    spy.mockRestore();
  });
});
