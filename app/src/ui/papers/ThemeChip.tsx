import { getThemeColor } from "../../core/constants/theme-colors";

interface Props {
  label: string;
  colorIndex: number;
}

export default function ThemeChip({ label, colorIndex }: Props) {
  const color = getThemeColor(colorIndex);

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ backgroundColor: color.bg, color: color.text }}
    >
      {label}
    </span>
  );
}
