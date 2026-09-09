import { NextRequest, NextResponse } from 'next/server';

/**
 * BFF proxy — injeta API_TOKEN server-side e encaminha para o backend.
 * O browser nunca recebe NEXT_PUBLIC_API_TOKEN.
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const API_TOKEN = process.env.API_TOKEN || '';

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
  const pathSegments = context.params.path ?? [];
  const path = pathSegments.map(encodeURIComponent).join('/');
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
    const message = err instanceof Error ? err.message : 'Falha ao contatar o backend.';
    return NextResponse.json({ detail: message }, { status: 502 });
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
