import { useState } from "react";
import { ChevronDown, ChevronRight, FileText } from "lucide-react";
import type { Paper } from "../../core/types/paper";
import ThemeChip from "./ThemeChip";

interface Props {
  papers: Paper[];
}

function PaperCard({ paper }: { paper: Paper }) {
  const [expanded, setExpanded] = useState(false);
  const themes = paper.themes || [];
  const claims = paper.claims || [];

  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-3 w-full px-4 py-3 text-left hover:bg-bg transition-colors"
      >
        {expanded ? (
          <ChevronDown size={16} className="text-text-muted shrink-0" />
        ) : (
          <ChevronRight size={16} className="text-text-muted shrink-0" />
        )}
        <FileText size={16} className="text-text-muted shrink-0" />
        <span className="flex-1 text-sm font-medium text-text-primary truncate">
          {paper.title}
        </span>
        <div className="flex gap-1 shrink-0">
          {themes.slice(0, 3).map((theme) => (
            <ThemeChip
              key={theme.id}
              label={theme.label}
              colorIndex={theme.colorIndex}
            />
          ))}
          {themes.length > 3 && (
            <span className="text-xs text-text-muted">
              +{themes.length - 3}
            </span>
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-border/50">
          {themes.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-text-secondary mb-1.5">
                Themes
              </p>
              <div className="flex flex-wrap gap-1.5">
                {themes.map((theme) => (
                  <ThemeChip
                    key={theme.id}
                    label={theme.label}
                    colorIndex={theme.colorIndex}
                  />
                ))}
              </div>
            </div>
          )}

          {claims.length > 0 && (
            <div>
              <p className="text-xs font-medium text-text-secondary mb-1.5">
                Claims ({claims.length})
              </p>
              <ul className="space-y-2">
                {claims.map((claim) => {
                  const theme = themes.find((t) => t.id === claim.themeId);
                  return (
                    <li key={claim.id} className="text-sm text-text-primary">
                      <p>{claim.text}</p>
                      <p className="text-xs text-text-muted mt-0.5">
                        p.{claim.page}, §{claim.paragraph}
                        {theme && (
                          <>
                            {" · "}
                            <span>
                              {theme.label}
                            </span>
                          </>
                        )}
                      </p>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {themes.length === 0 && claims.length === 0 && (
            <p className="text-sm text-text-muted italic">
              No extracted data yet.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function PaperCards({ papers }: Props) {
  return (
    <div className="flex flex-col h-full p-6">
      <h2 className="text-lg font-heading font-semibold text-text-primary mb-4">
        Papers ({papers.length})
      </h2>
      <div className="flex-1 overflow-y-auto space-y-2">
        {papers.map((paper) => (
          <PaperCard key={paper.id} paper={paper} />
        ))}
      </div>
    </div>
  );
}
