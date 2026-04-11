export interface Theme {
  id: string;
  label: string;
  colorIndex: number;
}

export interface Claim {
  id: string;
  text: string;
  page: number;
  paragraph: number;
  themeId: string;
}

export interface Paper {
  id: string;
  title: string;
  fileName: string;
  sizeBytes: number;
  addedAt: number;
  themes?: Theme[];
  claims?: Claim[];
}

export type ViewState = "empty" | "uploaded" | "complete";
