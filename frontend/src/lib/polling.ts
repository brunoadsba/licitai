/**
 * Polling com deadline, backoff exponencial, limite de falhas
 * e pausa enquanto a aba está oculta (`document.hidden`).
 */

export interface PollOptions<T> {
  /** Tempo máximo total em ms (default: 5 min). */
  deadlineMs?: number;
  /** Intervalo inicial em ms (default: 1000). */
  initialIntervalMs?: number;
  /** Teto do intervalo após backoff em ms (default: 10_000). */
  maxIntervalMs?: number;
  /** Multiplicador de backoff (default: 1.5). */
  backoffFactor?: number;
  /** Falhas consecutivas antes de abortar (default: 5). */
  maxFailures?: number;
  /** Pausa quando `document.hidden` (default: true). */
  pauseWhenHidden?: boolean;
  /** Chamado a cada resultado bem-sucedido. Retorne true para parar. */
  onResult?: (result: T) => boolean | void;
  /** Chamado a cada falha (antes de atingir maxFailures). */
  onError?: (err: unknown, consecutiveFailures: number) => void;
  /** Chamado ao estourar o deadline. */
  onDeadline?: () => void;
  /** Chamado ao atingir maxFailures. */
  onMaxFailures?: (err: unknown) => void;
  signal?: AbortSignal;
}

export interface PollHandle {
  /** Cancela o polling. */
  cancel: () => void;
  /** Promise que resolve quando o polling termina (done, cancel, deadline ou falhas). */
  done: Promise<void>;
}

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'));
      return;
    }
    const timer = setTimeout(resolve, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(new DOMException('Aborted', 'AbortError'));
    };
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

async function waitWhileHidden(signal?: AbortSignal): Promise<void> {
  if (typeof document === 'undefined' || !document.hidden) return;

  await new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'));
      return;
    }
    const onVisibility = () => {
      if (!document.hidden) {
        document.removeEventListener('visibilitychange', onVisibility);
        signal?.removeEventListener('abort', onAbort);
        resolve();
      }
    };
    const onAbort = () => {
      document.removeEventListener('visibilitychange', onVisibility);
      reject(new DOMException('Aborted', 'AbortError'));
    };
    document.addEventListener('visibilitychange', onVisibility);
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

/**
 * Inicia polling assíncrono. Retorna handle com `cancel` e `done`.
 *
 * @param fetchFn — função que busca o estado atual (deve usar skipCache nos GETs)
 * @param isDone — retorna true quando o estado final foi alcançado
 */
export function startPolling<T>(
  fetchFn: () => Promise<T>,
  isDone: (result: T) => boolean,
  options: PollOptions<T> = {}
): PollHandle {
  const {
    deadlineMs = 5 * 60 * 1000,
    initialIntervalMs = 1000,
    maxIntervalMs = 10_000,
    backoffFactor = 1.5,
    maxFailures = 5,
    pauseWhenHidden = true,
    onResult,
    onError,
    onDeadline,
    onMaxFailures,
    signal,
  } = options;

  const controller = new AbortController();
  const onExternalAbort = () => controller.abort();
  signal?.addEventListener('abort', onExternalAbort, { once: true });

  let cancelled = false;
  const cancel = () => {
    cancelled = true;
    controller.abort();
  };

  const done = (async () => {
    const startedAt = Date.now();
    let interval = initialIntervalMs;
    let consecutiveFailures = 0;
    let lastError: unknown;

    try {
      while (!cancelled && !controller.signal.aborted) {
        if (Date.now() - startedAt > deadlineMs) {
          onDeadline?.();
          return;
        }

        if (pauseWhenHidden) {
          await waitWhileHidden(controller.signal);
        }

        try {
          const result = await fetchFn();
          consecutiveFailures = 0;
          interval = initialIntervalMs;

          const stopFromCallback = onResult?.(result) === true;
          if (stopFromCallback || isDone(result)) {
            return;
          }
        } catch (err) {
          if (controller.signal.aborted || cancelled) return;
          consecutiveFailures += 1;
          lastError = err;
          onError?.(err, consecutiveFailures);
          if (consecutiveFailures >= maxFailures) {
            onMaxFailures?.(err);
            return;
          }
          interval = Math.min(interval * backoffFactor, maxIntervalMs);
        }

        await wait(interval, controller.signal);
      }
    } catch (err) {
      if ((err as Error)?.name === 'AbortError') return;
      throw err;
    } finally {
      signal?.removeEventListener('abort', onExternalAbort);
      void lastError;
    }
  })();

  return { cancel, done };
}

/**
 * Polling em loop até `isDone` (ou deadline / falhas). Útil fora de React effects.
 */
export async function pollUntil<T>(
  fetchFn: () => Promise<T>,
  isDone: (result: T) => boolean,
  options: PollOptions<T> = {}
): Promise<T | undefined> {
  let last: T | undefined;
  const handle = startPolling(fetchFn, isDone, {
    ...options,
    onResult: (result) => {
      last = result;
      return options.onResult?.(result);
    },
  });
  await handle.done;
  return last;
}
