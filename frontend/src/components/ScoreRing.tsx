export function ScoreRing({ score, max = 100 }: { score: number | null; max?: number }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const fraction = score === null ? 0 : Math.min(score / max, 1);
  return (
    <div className="relative h-36 w-36 shrink-0">
      <svg viewBox="0 0 120 120" className="-rotate-90" role="img" aria-label={`Score ${score ?? "unavailable"} out of ${max}`}>
        <defs>
          <linearGradient id="score-ring" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#0071e3" />
            <stop offset="1" stopColor="#7a5cff" />
          </linearGradient>
        </defs>
        <circle cx="60" cy="60" r={radius} fill="none" stroke="#ececf1" strokeWidth="10" />
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke="url(#score-ring)"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${fraction * circumference} ${circumference}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-semibold tracking-tight">{score ?? "—"}</span>
        <span className="text-xs text-muted">of {max}</span>
      </div>
    </div>
  );
}