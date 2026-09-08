const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

// Mesma política aplicada pelo backend (app/utils/security.py), cobrindo agora
// também as páginas servidas pelo Next.js — antes, a UI navegava sem CSP.
const SECURITY_HEADERS = [
  { key: 'Content-Security-Policy', value: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; connect-src 'self'" },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=()' },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    optimizePackageImports: ['lucide-react', 'framer-motion'],
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: SECURITY_HEADERS,
      },
    ];
  },
  // Proxy legado (/api/v1) coexiste com BFF Route Handler em /api/proxy/*
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${BACKEND_URL}/api/v1/:path*`,
      },
      {
        source: '/health',
        destination: `${BACKEND_URL}/health`,
      },
      {
        source: '/livez',
        destination: `${BACKEND_URL}/livez`,
      },
      {
        source: '/readyz',
        destination: `${BACKEND_URL}/readyz`,
      },
    ];
  },
};

module.exports = nextConfig;
