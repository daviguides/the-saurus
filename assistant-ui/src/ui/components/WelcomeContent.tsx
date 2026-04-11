import { useState } from "react";
import {
  Tags,
  BookOpen,
  FileSearch,
  Quote,
  GitMerge,
  Lightbulb,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import DinoFace from "../shared/DinoFace";

export type Suggestion = {
  id: string;
  title: string;
  description: string;
  prompt: string;
  icon: keyof typeof IconMap;
};

const IconMap = {
  tags: Tags,
  bookOpen: BookOpen,
  fileSearch: FileSearch,
  quote: Quote,
  gitMerge: GitMerge,
  lightbulb: Lightbulb,
};

const defaultSuggestions: Suggestion[] = [
  // Themes
  {
    id: "theme-1",
    title: "Theme Overview",
    description: "What thematic areas were identified across the papers?",
    prompt: "What are the main themes found across all papers?",
    icon: "tags",
  },
  {
    id: "theme-2",
    title: "Theme Connections",
    description: "Find how themes relate and overlap between papers",
    prompt: "Which themes appear in the most papers, and how do they connect?",
    icon: "gitMerge",
  },
  // Claims & Evidence
  {
    id: "claim-1",
    title: "Key Findings",
    description: "The most important claims and evidence from the corpus",
    prompt: "What are the strongest claims supported by multiple papers?",
    icon: "quote",
  },
  {
    id: "claim-2",
    title: "Contradictions",
    description: "Where do papers disagree or present conflicting evidence?",
    prompt: "Are there any disagreements or contradictions between papers?",
    icon: "lightbulb",
  },
  // Review & Analysis
  {
    id: "review-1",
    title: "Research Gaps",
    description: "Areas not covered or underexplored in the literature",
    prompt: "What research gaps were identified in the literature review?",
    icon: "fileSearch",
  },
  {
    id: "review-2",
    title: "Review Summary",
    description: "A concise summary of the generated literature review",
    prompt: "Summarize the main conclusions of the literature review.",
    icon: "bookOpen",
  },
];

interface WelcomeContentProps {
  onSuggestionClick: (prompt: string) => void;
  suggestions?: Suggestion[];
}

export default function WelcomeContent({
  onSuggestionClick,
  suggestions = defaultSuggestions,
}: WelcomeContentProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="flex flex-col items-center px-4 py-8">
      {/* Welcome header — dino face */}
      <div className="mb-4">
        <DinoFace size={88} className="text-primary" />
      </div>

      <h2 className="text-xl font-heading font-semibold text-text-primary mb-2">
        Ask about your papers
      </h2>
      <p className="text-sm text-text-secondary text-center max-w-md mb-8">
        Explore themes, claims, and insights extracted from your corpus.
        Ask anything about the papers or the generated literature review.
      </p>

      {/* Suggestions section */}
      <div className="w-full max-w-2xl">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center justify-between w-full px-4 py-2.5 mb-3 rounded-lg bg-surface border border-border text-text-primary hover:border-primary/30 transition-colors"
          aria-expanded={isExpanded}
          aria-controls="suggestions-panel"
        >
          <span className="text-sm font-medium">Try asking</span>
          {isExpanded ? (
            <ChevronUp size={16} className="text-text-muted" />
          ) : (
            <ChevronDown size={16} className="text-text-muted" />
          )}
        </button>

        {isExpanded && (
          <div
            id="suggestions-panel"
            className="grid grid-cols-1 sm:grid-cols-2 gap-2.5"
          >
            {suggestions.map((suggestion) => {
              const Icon = IconMap[suggestion.icon];
              return (
                <button
                  key={suggestion.id}
                  onClick={() => onSuggestionClick(suggestion.prompt)}
                  className="flex flex-col items-start p-3.5 rounded-lg border border-border hover:border-primary/40 hover:shadow-sm transition-all text-left group"
                >
                  <div className="p-1.5 rounded-md bg-primary/8 mb-2.5 group-hover:bg-primary/12 transition-colors">
                    <Icon size={16} className="text-primary" />
                  </div>
                  <h3 className="text-sm font-medium text-text-primary mb-0.5">
                    {suggestion.title}
                  </h3>
                  <p className="text-xs text-text-secondary line-clamp-2">
                    {suggestion.description}
                  </p>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
