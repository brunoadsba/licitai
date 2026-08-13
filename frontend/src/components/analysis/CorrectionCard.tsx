import type { CorrectionResponse } from '@/types';
import { CATEGORY_LABELS, SEVERITY_LABELS } from '@/types';
import { AGENT_ORIGIN_CONFIG, getCategoryBadge, getSeverityBadge } from '@/lib/badges';
import { useCopy } from '@/lib/useCopy';

interface CorrectionCardProps {
  correction: CorrectionResponse;
  index: number;
}

/**
 * Card DE → PARA de uma correção, com botões de cópia para o SEI.
 */
export default function CorrectionCard({ correction, index }: CorrectionCardProps) {
  const { copy, isCopied } = useCopy();
  const agent = correction.agent_origin ? AGENT_ORIGIN_CONFIG[correction.agent_origin] : null;

  return (
    <div key={correction.id} className="glass-card p-5 animate-slide-up" style={{ animationDelay: `${index * 80}ms` }}>
      {/* Header da correção */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          {agent && (
            <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border flex items-center gap-1 ${agent.badgeClass}`}>
              <span>{agent.icon}</span>
              {agent.label}
            </span>
          )}
          <span className={`badge ${getCategoryBadge(correction.category)}`}>
            {CATEGORY_LABELS[correction.category] || correction.category}
          </span>
          <span className={`badge ${getSeverityBadge(correction.severity)}`}>
            {SEVERITY_LABELS[correction.severity] || correction.severity}
          </span>
        </div>

        {/* Botão Principal de Copiar o PARA */}
        <button
          onClick={() => copy(correction.suggested_text, `para_${correction.id}`)}
          className="px-3 py-1.5 rounded-lg text-xs font-bold bg-green-500/20 hover:bg-green-500/30 text-green-300 border border-green-500/40 flex items-center gap-1.5 transition-all shadow-sm"
          title="Copiar texto de substituição para colar no SEI"
        >
          {isCopied(`para_${correction.id}`) ? (
            <>
              <svg className="w-3.5 h-3.5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              Texto Copiado!
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.757c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
              </svg>
              Copiar Texto Corrigido (PARA)
            </>
          )}
        </button>
      </div>

      {/* Problema */}
      <p className="text-sm text-gray-300 mb-4">{correction.problem}</p>

      {/* DE → PARA */}
      <div className="space-y-2 mb-4">
        <div className="diff-removed">
          <p className="text-xs text-red-400/70 font-semibold uppercase tracking-wider mb-1">DE (original)</p>
          <p className="text-sm text-red-300/90">{correction.original_text}</p>
        </div>
        <div className="diff-added relative group">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-green-400/70 font-semibold uppercase tracking-wider">PARA (sugerido)</p>
            <button
              onClick={() => copy(correction.suggested_text, `para_sub_${correction.id}`)}
              className="text-[11px] text-green-400/80 hover:text-green-300 underline"
            >
              {isCopied(`para_sub_${correction.id}`) ? 'Copiado!' : 'Copiar'}
            </button>
          </div>
          <p className="text-sm text-green-300/90">{correction.suggested_text}</p>
        </div>
      </div>

      {/* Justificativa e Fundamento Legal */}
      <div className="bg-surface-900/30 rounded-lg p-3 relative">
        <div className="flex items-center justify-between mb-1">
          <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider">Justificativa & Fundamentação</p>
          <button
            onClick={() =>
              copy(
                `${correction.justification}${correction.legal_basis ? ` (Fundamento: ${correction.legal_basis})` : ''}`,
                `just_${correction.id}`
              )
            }
            className="text-[11px] text-primary-400/80 hover:text-primary-300 underline"
          >
            {isCopied(`just_${correction.id}`) ? 'Copiado!' : 'Copiar Justificativa'}
          </button>
        </div>
        <p className="text-sm text-gray-400">{correction.justification}</p>
        {correction.legal_basis && (
          <p className="text-xs text-primary-400 mt-2 font-mono">
            📋 {correction.legal_basis}
          </p>
        )}
      </div>

      {/* Risco */}
      <div className="mt-3 flex items-start gap-2">
        <svg className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
        <p className="text-xs text-yellow-400/70">{correction.risk}</p>
      </div>
    </div>
  );
}
