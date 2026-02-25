// ─── Product ────────────────────────────────────────────────────────

export interface Product {
  id: number;
  external_id: string;
  platform: string;

  // Basic info
  title: string;
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
  vibe: string | null;
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
  primary_image: string | null;
  era: string | null;
  decade: string | null;
  fp_category: string | null;
  silhouette: string | null;
  vibe: string | null;
  material: string | null;
  ai_description: string | null;
  style_tags: string[];
  colors: string[];
}

export interface BridgeResult {
  id: number;
  source: ProductSummary;
  target: ProductSummary;
  bridge_score: number;
  text_similarity: number;
  image_similarity: number | null;
  structural_score: number;
  bridge_type: string | null;
  bridge_narrative: string | null;
  shared_attributes: Record<string, unknown>;
  created_at: string;
}

export interface BridgeListResponse {
  bridges: BridgeResult[];
  total: number;
  limit: number;
  offset: number;
}

export interface BridgeTypeStats {
  bridge_type: string;
  count: number;
  avg_score: number;
  min_score: number;
  max_score: number;
}

export interface ScoreHistogramBucket {
  bucket: string;
  count: number;
}

export interface BridgeStats {
  total_bridges: number;
  total_products_with_bridges: number;
  by_type: BridgeTypeStats[];
  score_histogram: ScoreHistogramBucket[];
}
