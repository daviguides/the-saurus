export interface ReviewClaim {
  text: string;
  page: number;
  paragraph: number;
  themeId: string;
}

export interface ReviewPaper {
  index: number;
  id: string;
  title: string;
  authors: string;
  year: string;
  journal: string;
  citedIn: string[];
  claims: ReviewClaim[];
}

export interface ReviewStats {
  paperCount: number;
  themeCount: number;
  claimCount: number;
  generationTimeMs: number;
}

export interface ReviewData {
  markdown: string;
  papers: ReviewPaper[];
  stats: ReviewStats;
  generatedAt: number;
}
