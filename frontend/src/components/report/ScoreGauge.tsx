interface ScoreGaugeProps {
  score: number | null;
  label: string;
}

/**
 * Gauge circular de pontuação (0-10) com cor por faixa.
 */
export default function ScoreGauge({ score, label }: ScoreGaugeProps) {
  const value = score ?? 0;
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 10) * circumference;

  const getColor = (s: number) => {
    if (s >= 8) return '#22c55e';
    if (s >= 6) return '#eab308';
    if (s >= 4) return '#f97316';
    return '#ef4444';
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-28 h-28">
        <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50" cy="50" r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="8"
          />
          <circle
            cx="50" cy="50" r={radius}
            fill="none"
            stroke={score !== null ? getColor(value) : 'rgba(255,255,255,0.1)'}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={score !== null ? offset : circumference}
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-white">
            {score !== null ? score.toFixed(1) : '—'}
          </span>
        </div>
      </div>
      <span className="text-xs text-gray-400 text-center">{label}</span>
    </div>
  );
}
