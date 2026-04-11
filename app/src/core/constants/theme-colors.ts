export interface ThemeColor {
  bg: string;
  text: string;
}

export const THEME_COLORS: ThemeColor[] = [
  { bg: "#E8F5E9", text: "#1B5E20" },
  { bg: "#E3F2FD", text: "#0D47A1" },
  { bg: "#FFF3E0", text: "#E65100" },
  { bg: "#F3E5F5", text: "#4A148C" },
  { bg: "#E0F7FA", text: "#006064" },
  { bg: "#FBE9E7", text: "#BF360C" },
  { bg: "#FFFDE7", text: "#F57F17" },
  { bg: "#ECEFF1", text: "#263238" },
];

export function getThemeColor(index: number): ThemeColor {
  return THEME_COLORS[index % THEME_COLORS.length];
}
