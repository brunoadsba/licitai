import { describe, expect, it } from 'vitest';
import { calibrationFor } from './calibration';

describe('calibrationFor', () => {
  it('cobertura total vira direta', () => {
    expect(calibrationFor(257, 257)).toEqual({ kind: 'direta' });
    expect(calibrationFor(100, 100)).toEqual({ kind: 'direta' });
  });

  it('cobertura < 95% vira faixa', () => {
    expect(calibrationFor(186, 257)).toEqual({ kind: 'faixa', analyzed: 186, total: 257 });
  });

  it('sem dados vira parcial-sem-cobertura', () => {
    expect(calibrationFor(null, 257)).toEqual({ kind: 'parcial-sem-cobertura' });
    expect(calibrationFor(0, 257)).toEqual({ kind: 'parcial-sem-cobertura' });
    expect(calibrationFor(5, 0)).toEqual({ kind: 'parcial-sem-cobertura' });
    expect(calibrationFor(undefined, undefined)).toEqual({ kind: 'parcial-sem-cobertura' });
    expect(calibrationFor(300, 257)).toEqual({ kind: 'parcial-sem-cobertura' });
    expect(calibrationFor(Number.NaN, 257)).toEqual({ kind: 'parcial-sem-cobertura' });
  });
});
