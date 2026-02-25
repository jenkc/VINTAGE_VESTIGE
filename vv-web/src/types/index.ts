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

  // Source metadata
  color: string | null;
  season: string | null;
  year: number | null;
  culture: string | null;
  period: string | null;
  object_date: string | null;

  // Enrichment fields (Claude-generated)
  era: string | null;
  decade: string | null;
  style_tags: string[];
  colors: string[];
  material: string | null;
  pattern: string | null;
  garment_type: string | null;
  vibe: string | null;
  fit_style: string | null;
  occasion: string | null;
  ai_description: string | null;
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
  title: string;
  category: string | null;
  primary_image: string | null;

  // Enrichment metadata returned from Qdrant payload
  era: string | null;
  decade: string | null;
  style_tags: string[];
  colors: string[];
  material: string | null;
  pattern: string | null;
  garment_type: string | null;
  vibe: string | null;
  fit_style: string | null;
  occasion: string | null;
  ai_description: string | null;
  season: string | null;
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
