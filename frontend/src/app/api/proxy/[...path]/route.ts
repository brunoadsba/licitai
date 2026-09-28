import { NextRequest, NextResponse } from 'next/server';

/**
 * BFF proxy — injeta API_TOKEN server-side e encaminha para o backend.
 * O browser nunca recebe NEXT_PUBLIC_API_TOKEN.
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const API_TOKEN = process.env.API_TOKEN || '';
const BFF_ALLOWED_ORIGINS = (process.env.BFF_ALLOWED_ORIGINS || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

function selfOrigins(request: NextRequest): Set<string> {
  const out = new Set<string>([request.nextUrl.origin]);
  const host = request.headers.get('host');
  if (host) {
    const proto = request.nextUrl.protocol || 'http:';
    out.add(`${proto}//${host}`);
    for (const loop of ['localhost', '127.0.0.1', '[::1]']) {
      out.add(
        `${proto}//${host.replace(/^(localhost|127\.0\.0\.1|\[::1\])/, loop)}`,
      );
    }
  }
  return out;
}

function isSameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get('origin');
  if (origin) {
    if (selfOrigins(request).has(origin)) return true;
    return BFF_ALLOWED_ORIGINS.includes(origin);
  }
  const site = request.headers.get('sec-fetch-site');
  if (site === 'same-origin') return true;
  if (site) {
    return (
      site === 'none' &&
      (request.method === 'GET' || request.method === 'HEAD')
    );
  }
  return request.method === 'GET' || request.method === 'HEAD';
}

const HOP_BY_HOP = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailers',
  'transfer-encoding',
  'upgrade',
  'host',
  'content-length',
]);

async function proxyRequest(
  request: NextRequest,
  context: { params: { path: string[] } }
): Promise<NextResponse> {
  if (!isSameOrigin(request)) {
    return NextResponse.json({ detail: 'Origem não permitida.' }, { status: 403 });
  }
  const pathSegments = context.params.path ?? [];
  // Aceita /api/proxy/documents e /api/proxy/v1/documents (evita /api/v1/v1/...).
  const normalizedSegments =
    pathSegments[0] === 'v1' ? pathSegments.slice(1) : pathSegments;
  const path = normalizedSegments.map(encodeURIComponent).join('/');
  const search = request.nextUrl.search;
  const targetUrl = `${BACKEND_URL}/api/v1/${path}${search}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (HOP_BY_HOP.has(key.toLowerCase())) return;
    if (key.toLowerCase() === 'x-api-token') return;
    headers.set(key, value);
  });
  if (API_TOKEN) {
    headers.set('X-API-Token', API_TOKEN);
  }
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  const init: RequestInit = {
    method: request.method,
    headers,
  };

  if (request.method !== 'GET' && request.method !== 'HEAD') {
    const body = await request.arrayBuffer();
    if (body.byteLength > 0) {
      init.body = body;
    }
  }

  try {
    const upstream = await fetch(targetUrl, init);
    const responseHeaders = new Headers();
    upstream.headers.forEach((value, key) => {
      if (HOP_BY_HOP.has(key.toLowerCase())) return;
      responseHeaders.set(key, value);
    });

    return new NextResponse(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (err) {
    console.error('BFF proxy falhou:', targetUrl, err);
    return NextResponse.json({ detail: 'Falha ao contatar o backend.' }, { status: 502 });
  }
}

export async function GET(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyRequest(request, context);
}

export async function POST(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyRequest(request, context);
}

export async function PUT(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyRequest(request, context);
}

export async function PATCH(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyRequest(request, context);
}

export async function DELETE(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyRequest(request, context);
}
