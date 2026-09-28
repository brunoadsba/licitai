/** Calibragem da nota: cobertura < 95% vira faixa + ressalva, nunca nota seca. */

export type Calibration =
  | { kind: 'direta' }
  | { kind: 'faixa'; analyzed: number; total: number }
  | { kind: 'parcial-sem-cobertura' };

export const COVERAGE_THRESHOLD = 0.95;

export function calibrationFor(
  analyzed: number | null | undefined,
  total: number | null | undefined,
): Calibration {
  if (
    analyzed == null ||
    total == null ||
    !Number.isFinite(analyzed) ||
    !Number.isFinite(total) ||
    total <= 0 ||
    analyzed > total
  ) {
    return { kind: 'parcial-sem-cobertura' };
  }
  if (analyzed <= 0) return { kind: 'parcial-sem-cobertura' };
  if (analyzed / total < COVERAGE_THRESHOLD) {
    return { kind: 'faixa', analyzed, total };
  }
  return { kind: 'direta' };
}
