/**
 * Núcleo do cliente API (BFF proxy + cache + erros) — extraído de `lib/api.ts`.
 *
 * Chamadas do browser passam pelo BFF (`/api/proxy/...`), que encaminha
 * para `/api/v1/...` e injeta `API_TOKEN` server-side. O token nunca vai para o client.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function extractErrorMessage(err: unknown, fallback = 'Erro inesperado.'): string {
  if (err instanceof ApiError || err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  return fallback;
}

type FetchAPIOptions = RequestInit & { timeoutMs?: number; skipCache?: boolean };

const CACHE_TTL_MS = 30_000;
const apiCache = new Map<string, { expiry: number; data: unknown }>();
const inflightRequests = new Map<string, Promise<unknown>>();

function getCacheKey(endpoint: string, options: FetchAPIOptions): string | null {
  const method = (options.method || 'GET').toUpperCase();
  if (method !== 'GET') return null;
  if (options.skipCache) return null;
  if (typeof window === 'undefined') return null;
  return `${method}:${endpoint}`;
}

function invalidateCache(prefix?: string) {
  if (typeof window === 'undefined') return;
  if (!prefix) {
    apiCache.clear();
    return;
  }
  for (const key of Array.from(apiCache.keys())) {
    if (key.includes(prefix)) apiCache.delete(key);
  }
}

export function clearApiCache() {
  apiCache.clear();
  inflightRequests.clear();
}

export async function fetchAPI<T>(endpoint: string, options: FetchAPIOptions = {}): Promise<T> {
  const url = `${API_BASE}/api/proxy${endpoint}`;
  const { timeoutMs = 30_000, skipCache: _skipCache, ...requestInit } = options;

  const cacheKey = getCacheKey(endpoint, options);
  if (cacheKey) {
    const cached = apiCache.get(cacheKey);
    if (cached && cached.expiry > Date.now()) {
      return cached.data as T;
    }
    const inflight = inflightRequests.get(cacheKey);
    if (inflight) {
      return inflight as Promise<T>;
    }
  }

  const doFetch = async (): Promise<T> => {
    const response = await fetch(url, {
      ...requestInit,
      signal: options.signal ?? AbortSignal.timeout(timeoutMs),
      headers: {
        'Accept': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      let errorMessage = `Erro ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch {
        // Response body não é JSON
      }
      throw new ApiError(errorMessage, response.status);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    const data = (await response.json()) as T;
    if (cacheKey) {
      apiCache.set(cacheKey, { expiry: Date.now() + CACHE_TTL_MS, data });
    }
    return data;
  };

  if (cacheKey) {
    const promise = doFetch().finally(() => {
      inflightRequests.delete(cacheKey);
    });
    inflightRequests.set(cacheKey, promise as Promise<unknown>);
    return promise;
  }

  const result = await doFetch();
  const method = (options.method || 'GET').toUpperCase();
  if (method !== 'GET') {
    const prefix = endpoint.split('/')[1] || '';
    if (prefix) invalidateCache(prefix);
    else invalidateCache();
  }
  return result
}

export function jsonBody(data: unknown): BodyInit {
  return JSON.stringify(data);
}
