import { describe, expect, it, vi } from 'vitest';
import { pollUntil, startPolling } from './polling';

const fast = {
  initialIntervalMs: 5,
  maxIntervalMs: 10,
  backoffFactor: 1,
  deadlineMs: 2000,
};

describe('pollUntil', () => {
  it('retorna quando isDone', async () => {
    let n = 0;
    const out = await pollUntil(
      async () => ++n,
      (v) => v >= 3,
      fast,
    );
    expect(out).toBe(3);
  });

  it('onResult true para cedo', async () => {
    const seen: number[] = [];
    const out = await pollUntil(async () => 1, () => false, {
      ...fast,
      onResult: (v) => {
        seen.push(v);
        return true;
      },
    });
    expect(out).toBe(1);
    expect(seen).toEqual([1]);
  });

  it('maxFailures chama onMaxFailures', async () => {
    const onMaxFailures = vi.fn();
    const out = await pollUntil(
      async () => {
        throw new Error('boom');
      },
      () => false,
      { ...fast, maxFailures: 2, onMaxFailures },
    );
    expect(out).toBeUndefined();
    expect(onMaxFailures).toHaveBeenCalledTimes(1);
  });

  it('deadline chama onDeadline', async () => {
    const onDeadline = vi.fn();
    await pollUntil(async () => 0, () => false, {
      ...fast,
      deadlineMs: 30,
      onDeadline,
    });
    expect(onDeadline).toHaveBeenCalledTimes(1);
  });
});

describe('startPolling cancel', () => {
  it('cancel interrompe o loop', async () => {
    let calls = 0;
    const handle = startPolling(
      async () => ++calls,
      () => false,
      fast,
    );
    handle.cancel();
    await handle.done;
    expect(calls).toBeLessThanOrEqual(1);
  });
});
