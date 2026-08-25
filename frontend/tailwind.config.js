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
        // ── Tokens semânticos (ver frontend/DESIGN.md §2 — paleta CODEBA) ─
        canvas: 'var(--canvas)',
        panel: 'var(--panel)',
        elevated: {
          DEFAULT: 'var(--surface)',
          hover: 'var(--surface-hover)',
        },
        // CODEBA — identidade portuária (navy #051853, azul #0355CF, teal #3AA4A4)
        codeba: {
          navy: '#051853',
          blue: '#0355CF',
          teal: '#3AA4A4',
          gray: '#606163',
        },
        // Acento único teal CODEBA — única cor cromática interativa
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
      animation: {
        'fade-in': 'fadeIn 0.3s cubic-bezier(0.32, 0.72, 0, 1)',
        'slide-up': 'slideUp 0.35s cubic-bezier(0.32, 0.72, 0, 1)',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'gauge-fill': 'gaugeFill 1.5s ease-out forwards',
        shimmer: 'shimmer 2s linear infinite',
        overlayIn: 'overlayIn 150ms ease-out',
        contentIn: 'contentIn 200ms cubic-bezier(0.32, 0.72, 0, 1)',
        menuIn: 'menuIn 150ms cubic-bezier(0.32, 0.72, 0, 1)',
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
        overlayIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        contentIn: {
          '0%': { opacity: '0', transform: 'translate(-50%, -48%) scale(0.97)' },
          '100%': { opacity: '1', transform: 'translate(-50%, -50%) scale(1)' },
        },
        menuIn: {
          '0%': { opacity: '0', transform: 'scale(0.97)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
};
