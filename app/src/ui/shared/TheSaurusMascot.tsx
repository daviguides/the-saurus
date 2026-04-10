interface Props {
  size?: number;
  className?: string;
}

export default function TheSaurusMascot({ size = 120, className }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-label="The Saurus mascot"
    >
      {/* Body */}
      <ellipse cx="55" cy="72" rx="28" ry="22" />
      {/* Neck */}
      <path d="M45 55 Q38 38 42 25" />
      <path d="M55 52 Q50 38 48 25" />
      {/* Head */}
      <ellipse cx="45" cy="22" rx="12" ry="9" />
      {/* Eye */}
      <circle cx="40" cy="20" r="2" fill="currentColor" stroke="none" />
      {/* Smile */}
      <path d="M36 25 Q40 28 46 25" />
      {/* Tail */}
      <path d="M83 68 Q95 60 100 50 Q102 46 98 48" />
      {/* Legs */}
      <path d="M40 92 L38 108" />
      <path d="M48 92 L46 108" />
      <path d="M62 92 L64 108" />
      <path d="M70 92 L72 108" />
      {/* Feet */}
      <path d="M35 108 L42 108" />
      <path d="M43 108 L50 108" />
      <path d="M61 108 L68 108" />
      <path d="M69 108 L76 108" />
      {/* Back plates */}
      <path d="M50 50 L48 42 L54 48" />
      <path d="M58 52 L58 44 L64 50" />
      <path d="M66 56 L68 48 L72 55" />
    </svg>
  );
}
