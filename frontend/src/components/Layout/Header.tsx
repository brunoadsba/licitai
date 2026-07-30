'use client';

import { usePathname } from 'next/navigation';

const BREADCRUMB_MAP: Record<string, string> = {
  '/': 'Painel',
  '/upload': 'Enviar Documento',
  '/analysis': 'Análise',
  '/report': 'Relatório',
};

export default function Header() {
  const pathname = usePathname();

  // Construir breadcrumb
  const parts = pathname.split('/').filter(Boolean);
  const title = BREADCRUMB_MAP[pathname] || parts[0] || 'Painel';

  return (
    <header className="sticky top-0 z-40 px-6 lg:px-8 py-4 bg-surface-950/60 backdrop-blur-xl border-b border-white/[0.04]">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
            <span>SEI</span>
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
            <span className="text-gray-400">{title}</span>
          </div>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
        </div>

        {/* Indicador do provedor LLM */}
        <div className="flex items-center gap-3">
          <div className="glass-card px-4 py-2 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary-400" />
            <span className="text-xs text-gray-400">IA Ativa</span>
          </div>
        </div>
      </div>
    </header>
  );
}
