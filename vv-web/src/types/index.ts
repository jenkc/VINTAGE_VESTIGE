// ─── Product ────────────────────────────────────────────────────────

export interface Product {
  id: number;
  external_id: string;
  platform: string;

  // Basic info
  title: string;
  display_title: string | null;
  description: string | null;
  category: string | null;
  price: number | null;
  currency: string;

  // Images
  primary_image: string | null;
  image_urls: string[] | null;

  // Source Metadata
  culture: string | null;
  object_date: string | null;

  // Enrichment fields (Claude-generated)
  era: string | null;
  decade: string | null;
  style_tags: string[];
  colors: string[];
  material: string | null;
  garment_type: string | null;
  vibe_scores: Record<string, [string, number] | null> | null;
  fit_style: string | null;
  occasion: string | null;
  ai_description: string | null;

  // Fashionpedia taxonomy
  fp_category: string | null;
  silhouette: string | null;
  neckline: string | null;
  waistline: string | null;
  length: string | null;
  sleeve_length: string | null;
  opening_type: string | null;
  textile_pattern: string | null;
  textile_finishing: string[];
  nickname: string | null;
  garment_parts: string[];
  decorations: string[];

  // Cross-cultural
  construction_technique: string[];
  social_function: string[];
  motif_family: string[];

  // Knowledge graph fields
  designer: string | null;
  influence_references: string[];
  production_mode: string | null;
  material_origin: string | null;
  garment_system: string[];
  named_movements: string[];
}

// ─── Search ─────────────────────────────────────────────────────────

export interface SearchFilters {
  era?: string;
  decade?: string;
  garment_type?: string;
  vibe?: string;
  occasion?: string;
  fit_style?: string;
  culture?: string;
  material?: string;
}

export interface TextSearchRequest {
  query: string;
  limit?: number;
  filters?: SearchFilters;
}

export interface ImageSearchRequest {
  image: string; // base64 data URL
  limit?: number;
}

export interface SearchResult {
  id: number;
  score: number;
  platform: string;
  title: string;
  category: string | null;
  primary_image: string | null;

  // Enrichment metadata returned from Qdrant payload
  era: string | null;
  decade: string | null;
  style_tags: string[];
  colors: string[];
  material: string | null;
  garment_type: string | null;
  vibe: string | null;
  fit_style: string | null;
  occasion: string | null;
  ai_description: string | null;
  culture: string | null;
  object_date: string | null;
  price: number | null;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total: number;
}

// ─── Filters (fetched from database) ────────────────────────────────

export interface FilterOptions {
  eras: string[];
  decades: string[];
  vibes: string[];
  garment_types: string[];
  occasions: string[];
  fit_styles: string[];
  cultures: string[];
  materials: string[];
}


// ─── Bridges ───────────────────────────────────────────────────────

export interface ProductSummary {
  id: number;
  platform: string;
  title: string;
  display_title: string | null;
  primary_image: string | null;
  era: string | null;
  decade: string | null;
  fp_category: string | null;
  silhouette: string | null;
  material: string | null;
  culture: string | null;
  ai_description: string | null;
  style_tags: string[];
  colors: string[];
  vibe_scores: Record<string, [string, number] | null> | null;
  designer: string | null;
  named_movements: string[];
  influence_references: string[];
  production_mode: string | null;
}

/** Entity-based shared connection data — the "why" of the bridge */
export interface SharedEntities {
  designer?: string[];
  named_movements?: string[];
  construction_technique?: string[];
  social_function?: string[];
  motif_family?: string[];
  garment_system?: string[];
  influence_references?: string[];
  lineage_reference?: string;       // only on lineage bridges
  lineage_match_score?: number;     // only on lineage bridges
  image_similarity?: number;        // only on visual_echo bridges
}

export interface BridgeResult {
  id: number;
  source: ProductSummary;
  target: ProductSummary;

  // Scores
  bridge_score: number | null;
  entity_score: number | null;
  text_similarity: number | null;
  image_similarity: number | null;

  // Classification
  connection_mode: 'shared_entity' | 'lineage' | 'visual_echo' | null;
  crossing_type: string | null;
  year_gap: number | null;
  directed: boolean;

  // Entity data
  shared_entities: SharedEntities;

  // Narrative
  bridge_narrative: string | null;
  created_at: string | null;
}

export interface BridgeListResponse {
  bridges: BridgeResult[];
  total: number;
  limit: number;
  offset: number;
}

export interface ConnectionModeStats {
  connection_mode: string;
  count: number;
  avg_score: number;
}

export interface ScoreHistogramBucket {
  bucket: string;
  count: number;
}

export interface BridgeStats {
  total_bridges: number;
  total_products_with_bridges: number;
  by_mode: ConnectionModeStats[];
  score_histogram: ScoreHistogramBucket[];
}

// ─── Explore ──────────────────────────────────────────────────────

export interface FunctionSummary {
  function: string;
  count: number;
}

export interface FunctionListResponse {
  functions: FunctionSummary[];
  total: number;
}

export interface FunctionDetailResponse {
  function: string;
  products: ProductSummary[];
  total: number;
  limit: number;
  offset: number;
}