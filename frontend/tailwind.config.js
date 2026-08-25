/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // ── Tokens semânticos (ver frontend/DESIGN.md §2) ──────────────
        canvas: 'var(--canvas)',
        panel: 'var(--panel)',
        elevated: {
          DEFAULT: 'var(--surface)',
          hover: 'var(--surface-hover)',
        },
        // Acento único teal-petróleo — única cor cromática do sistema
        accent: {
          50: '#ECFCF9',
          100: '#D0F7F0',
          200: '#A3EEE3',
          300: '#71DFCF',
          400: '#43C9B9',
          500: '#2AAFA0',
          600: '#1F8E83',
          700: '#1B7268',
          800: '#185B54',
          900: '#14453F',
          950: '#0A2E2A',
        },
        content: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
          subtle: 'var(--text-subtle)',
        },
        line: {
          subtle: 'var(--border-subtle)',
          strong: 'var(--border-strong)',
        },
        risk: {
          low: '#22c55e',
          medium: '#eab308',
          high: '#f97316',
          critical: '#ef4444',
        },

        // ── Aliases LEGADOS (remover após Fase 3 migrar todas as páginas) ──
        primary: {
          50: '#ECFCF9',
          100: '#D0F7F0',
          200: '#A3EEE3',
          300: '#71DFCF',
          400: '#43C9B9',
          500: '#2AAFA0',
          600: '#1F8E83',
          700: '#1B7268',
          800: '#185B54',
          900: '#14453F',
          950: '#0A2E2A',
        },
        surface: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          700: '#1D232E',
          800: '#171C25',
          900: '#11151C',
          950: '#0B0E13',
        },
      },
      fontFamily: {
        sans: ['var(--font-geist-sans)', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['var(--font-geist-mono)', 'ui-monospace', 'SF Mono', 'Menlo', 'monospace'],
      },
      borderRadius: {
        // raio padrão de botões/inputs sobe de xl→md conforme DESIGN.md §4
      },
      boxShadow: {
        // Elevação por luminância + rim light — sombras escuras quase invisíveis em dark
        rim: 'inset 0 1px 0 rgba(255,255,255,0.06)',
        dialog:
          '0 8px 40px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06)',
        drawer: '8px 0 40px rgba(0,0,0,0.4)',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        gaugeFill: {
          '0%': { strokeDashoffset: '283' },
          '100%': { strokeDashoffset: 'var(--gauge-offset)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.3s cubic-bezier(0.32, 0.72, 0, 1)',
        'slide-up': 'slideUp 0.35s cubic-bezier(0.32, 0.72, 0, 1)',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'gauge-fill': 'gaugeFill 1.5s ease-out forwards',
        shimmer: 'shimmer 2s linear infinite',
      },
    },
  },
  plugins: [],
};
