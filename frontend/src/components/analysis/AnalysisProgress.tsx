import type { AnalysisDetailResponse } from '@/types';

interface AnalysisProgressProps {
  analysis: AnalysisDetailResponse;
}

/**
 * Barra de progresso da análise em execução com shimmer e badges dos agentes ativos.
 */
export default function AnalysisProgress({ analysis }: AnalysisProgressProps) {
  const pct = Math.min(100, Math.round(((analysis.analyzed_items || 0) / (analysis.total_items || 1)) * 100));

  return (
    <div role="status" className="glass-card p-5 border-primary-500/30 glow space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center">
            <div className="w-3 h-3 rounded-full bg-cyan-400 animate-ping absolute opacity-75" />
            <div className="w-3 h-3 rounded-full bg-cyan-500" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>🤖 Orquestrador Multi-Agente em Execução...</span>
            </h3>
            <p className="text-xs text-gray-400">
              Avaliando conformidade do TR com 4 agentes especializados (Lei 14.133/21 & TCU)
            </p>
          </div>
        </div>

        <div className="text-right">
          <span className="text-xl font-extrabold text-cyan-400 font-mono">
            {pct}%
          </span>
          <span className="text-xs text-gray-400 block font-mono">
            {analysis.analyzed_items} de {analysis.total_items} itens processados
          </span>
        </div>
      </div>

      {/* Barra de Progresso com Shimmer */}
      <div className="progress-bar">
        <div
          className="progress-bar-fill"
          style={{
            width: `${Math.min(100, Math.max(4, pct))}%`,
          }}
        />
      </div>

      {/* Badges dos Agentes Ativos */}
      <div className="flex items-center gap-2 pt-1 overflow-x-auto">
        <span className="text-[11px] text-gray-400 font-semibold mr-1">Agentes Ativos:</span>
        <span className="badge badge-juridica text-[10px] animate-pulse">⚖️ Jurídico</span>
        <span className="badge badge-tecnica text-[10px] animate-pulse">🛠️ Técnico</span>
        <span className="badge badge-redacao text-[10px] animate-pulse">✍️ Redação</span>
        <span className="badge badge-estrutural text-[10px] animate-pulse">📐 Estrutural</span>
      </div>
    </div>
  );
}
