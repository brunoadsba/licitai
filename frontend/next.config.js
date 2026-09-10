const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

// CSP alinhada ao backend, com exceção necessária ao Next.js App Router:
// o runtime injeta <script> inline de hidratação/RSC — sem 'unsafe-inline'
// (ou nonce por request) a UI fica quebrada no browser.
const SECURITY_HEADERS = [
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data:",
      "font-src 'self' data:",
      "frame-ancestors 'none'",
      "object-src 'none'",
      "base-uri 'self'",
      "connect-src 'self'",
    ].join('; '),
  },
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
        source: '/favicon.ico',
        destination: '/logo-codeba.png',
      },
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
      {
        source: '/metrics',
        destination: `${BACKEND_URL}/metrics`,
      },
    ];
  },
};
module.exports = nextConfig;
