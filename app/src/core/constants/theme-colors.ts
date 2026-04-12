export interface ThemeColor {
  bg: string;
  text: string;
}

const THEME_COLOR_COUNT = 8;

export const THEME_COLORS: ThemeColor[] = Array.from({ length: THEME_COLOR_COUNT }, (_, i) => ({
  bg: `var(--saurus-theme-chip-${i}-bg)`,
  text: `var(--saurus-theme-chip-${i}-text)`,
}));

export function getThemeColor(index: number): ThemeColor {
  return THEME_COLORS[index % THEME_COLORS.length];
}
