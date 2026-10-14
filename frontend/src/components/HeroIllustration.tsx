export function HeroIllustration() {
  return (
    <svg
      viewBox="0 0 480 400"
      role="img"
      aria-label="Illustration of a resume card with an analysis score"
      className="h-auto w-full"
    >
      <defs>
        <linearGradient id="hero-blob" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#bfdcff" />
          <stop offset="1" stopColor="#e6d9ff" />
        </linearGradient>
        <linearGradient id="hero-ring" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#0071e3" />
          <stop offset="1" stopColor="#7a5cff" />
        </linearGradient>
        <filter id="hero-shadow" x="-20%" y="-20%" width="140%" height="150%">
          <feDropShadow dx="0" dy="12" stdDeviation="14" floodColor="#000" floodOpacity="0.12" />
        </filter>
      </defs>
      <path
        d="M70 200c0-90 80-150 180-140s170 70 160 160-90 150-190 140S70 290 70 200z"
        fill="url(#hero-blob)"
      />
      <g filter="url(#hero-shadow)">
        <rect x="110" y="64" width="230" height="272" rx="22" fill="#fff" />
      </g>
      <circle cx="158" cy="116" r="22" fill="#e8e8ed" />
      <rect x="192" y="100" width="104" height="11" rx="5.5" fill="#1d1d1f" />
      <rect x="192" y="122" width="72" height="8" rx="4" fill="#c7c7cc" />
      <rect x="138" y="168" width="174" height="8" rx="4" fill="#e8e8ed" />
      <rect x="138" y="190" width="150" height="8" rx="4" fill="#e8e8ed" />
      <rect x="138" y="212" width="164" height="8" rx="4" fill="#e8e8ed" />
      <rect x="138" y="246" width="54" height="22" rx="11" fill="#e8f1fd" />
      <rect x="200" y="246" width="64" height="22" rx="11" fill="#efeafd" />
      <rect x="272" y="246" width="40" height="22" rx="11" fill="#e8f1fd" />
      <g transform="translate(330 262)" filter="url(#hero-shadow)">
        <circle r="64" fill="#fff" />
      </g>
      <g transform="translate(330 262) rotate(-90)">
        <circle r="46" fill="none" stroke="#ececf1" strokeWidth="10" />
        <circle
          r="46"
          fill="none"
          stroke="url(#hero-ring)"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray="250 289"
        />
      </g>
      <text x="330" y="272" textAnchor="middle" fontSize="30" fontWeight="600" fill="#1d1d1f">
        87
      </text>
    </svg>
  );
}