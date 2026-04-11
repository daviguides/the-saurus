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
            stroke="#82A78F"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            aria-label="O mascote The Saurus devorando documentos"
        >
            {/* 1. Documentos / Papers */}
            <g strokeWidth="1.5">
                {/* Documento sendo devorado */}
                <g transform="rotate(-15 25 30)">
                    <rect x="12" y="25" width="14" height="18" rx="1.5" />
                    <line x1="15" y1="29" x2="23" y2="29" strokeWidth="1" />
                    <line x1="15" y1="33" x2="21" y2="33" strokeWidth="1" />
                    <line x1="15" y1="37" x2="23" y2="37" strokeWidth="1" />
                </g>
            </g>

            {/* 2. Corpo Principal (T-Rex) em Linha Contínua */}
            <path
                strokeWidth="2"
                d="M 38 50 C 30 48, 26 48, 26 44 L 38 36 L 22 28 C 25 18, 38 15, 48 22 C 55 28, 52 40, 52 50 C 52 65, 62 70, 75 70 C 90 70, 105 75, 105 85 C 105 92, 98 95, 92 88 C 86 80, 82 80, 80 80 L 80 105 C 80 107, 72 107, 72 105 L 72 85 C 65 92, 55 92, 48 85 L 48 105 C 48 107, 40 107, 40 105 L 40 75 C 40 60, 38 55, 38 50 Z"
            />

            {/* 3. Óculos e Olho (Estilo Thesaurus) */}
            <circle cx="40" cy="26" r="3.5" strokeWidth="1.5" />
            <path d="M 43.5 26 L 50 25" strokeWidth="1.5" />
            <circle cx="39" cy="26" r="1" fill="#82A78F" stroke="none" />

            {/* 4. Bracinhos de T-Rex */}
            <path d="M 44 62 L 34 65 L 34 69 M 34 65 L 37 69" strokeWidth="1.5" />

            {/* 5. Placas nas costas */}
            <path d="M 58 68 L 60 60 L 63 69" strokeWidth="1.5" strokeLinejoin="miter" />
            <path d="M 68 70 L 71 62 L 74 71" strokeWidth="1.5" strokeLinejoin="miter" />
            <path d="M 80 72 L 83 65 L 86 74" strokeWidth="1.5" strokeLinejoin="miter" />
        </svg>
    );
}
