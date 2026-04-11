interface Props {
  size?: number;
  className?: string;
}

/**
 * The Saurus mascot face — friendly dino head with glasses.
 * Used in assistant welcome screen. Happy expression, ready to help.
 */
export default function DinoFace({ size = 48, className }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-label="The Saurus assistant"
    >
      {/* Head outline — rounded dino head shape */}
      <path
        strokeWidth="1.8"
        d="M 14 30 C 8 28, 6 26, 6 22 L 14 16 L 4 10 C 6 3, 16 0, 24 6 C 30 11, 34 14, 36 20 C 38 26, 36 30, 30 32 C 24 34, 18 33, 14 30 Z"
      />

      {/* Glasses — round frame */}
      <circle cx="20" cy="16" r="4.5" strokeWidth="1.5" />
      {/* Glasses arm */}
      <path d="M 24.5 16 L 32 14" strokeWidth="1.5" />

      {/* Eye — happy, slightly closed (arc instead of dot) */}
      <path d="M 18 15.5 Q 20 13, 22 15.5" strokeWidth="1.5" fill="none" />

      {/* Happy smile */}
      <path d="M 10 24 Q 14 28, 20 26" strokeWidth="1.5" fill="none" />

      {/* Nostril */}
      <circle cx="8" cy="20" r="0.8" fill="currentColor" stroke="none" />

      {/* Little tooth */}
      <line x1="12" y1="24" x2="12" y2="26" strokeWidth="1.2" />

      {/* Spikes on top */}
      <path d="M 26 8 L 28 2 L 30 9" strokeWidth="1.3" />
      <path d="M 31 12 L 34 7 L 35 14" strokeWidth="1.3" />
    </svg>
  );
}
