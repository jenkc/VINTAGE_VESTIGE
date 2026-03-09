// Platform display colors (for dynamic styling)
export const PLATFORM_COLORS: Record<string, string> = {
  met_museum: "#8B2332",
  smithsonian: "#2E5A88",
  fashionpedia: "#5C7A5E",
  etsy: "#D35400",
  depop: "#FF2300",
};

// Platform display names (API returns slugs like "met_museum")
export const PLATFORM_NAMES: Record<string, string> = {
  met_museum: "The Met",
  smithsonian: "Smithsonian",
  fashionpedia: "Fashionpedia",
  etsy: "Etsy",
  depop: "Depop",
};

// Score breakdown bar colors
export const SCORE_COLORS = {
  semantic: "#2E5A88",
  visual: "#8B5E3C",
  structural: "#7A8B6F",
};

// Returns a color based on score value (for ScoreCircle, etc.)
export function scoreColorByValue(score: number): string {
  if (score > 0.8) return "#C4553A"; // terracotta
  if (score > 0.6) return "#B8924A"; // gold
  return "#8A7E74";                  // muted
}

export const CONNECTION_MODE_COLORS: Record<string, string> = {
  contrast: "#B5576D",    // rose
  resonance: "#B8924A",   // amber/gold
  affinity: "#8A7E74",    // muted
};

export const CONNECTION_MODE_LABELS: Record<string, string> = {
  contrast: "Contrast",
  resonance: "Resonance",
  affinity: "Affinity",
};