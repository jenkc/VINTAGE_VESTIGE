// Platform display colors (text only — never used as fills)
export const PLATFORM_COLORS: Record<string, string> = {
  met_museum: "#8B2332",
  smithsonian: "#2E5A88",
  fashionpedia: "#6B6B6B",
  va_museum: "#4A4A4A",
};

// Platform display names (API returns slugs like "met_museum")
export const PLATFORM_NAMES: Record<string, string> = {
  met_museum: "THE MET",
  smithsonian: "SMITHSONIAN",
  fashionpedia: "FASHIONPEDIA",
  va_museum: "V&A",
};

// Score breakdown — signal colors for data viz
export const SCORE_COLORS = {
  text: "#2E5A88",
  image: "#8B5E3C",
  entity: "#7A8B6F",
};

// Connection mode colors
export const CONNECTION_MODE_COLORS: Record<string, string> = {
  shared_entity: "#6B6B6B",    // grey — most common, neutral
  lineage: "#C4553A",           // accent — most interesting
  visual_echo: "#8B5E3C",      // brown — visual connection
};

// Connection mode labels
export const CONNECTION_MODE_LABELS: Record<string, string> = {
  shared_entity: "SHARED",
  lineage: "LINEAGE",
  visual_echo: "VISUAL ECHO",
};

// Entity type labels — human-readable names for shared_entities keys
export const ENTITY_TYPE_LABELS: Record<string, string> = {
  designer: "Designer",
  named_movements: "Movement",
  construction_technique: "Technique",
  social_function: "Function",
  motif_family: "Motif",
  garment_system: "Worn with",
  influence_references: "Influences",
};
