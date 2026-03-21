import { API_BASE_URL, DEFAULT_SEARCH_LIMIT } from "./constants";
import type {
  SearchResponse,
  SearchFilters,
  FilterOptions,
  Product,
  BridgeListResponse,
  BridgeResult,
  BridgeStats,
  FunctionListResponse,
  FunctionDetailResponse,
} from "@/types";

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

// ─── Text Search ────────────────────────────────────────────────────

export async function searchByText(
  query: string,
  filters?: SearchFilters,
  limit: number = DEFAULT_SEARCH_LIMIT
): Promise<SearchResponse> {
  return fetchAPI<SearchResponse>("/search/text", {
    method: "POST",
    body: JSON.stringify({ query, limit, filters }),
  });
}

// ─── Image Search ───────────────────────────────────────────────────

export async function searchByImage(
  image: string,
  limit: number = DEFAULT_SEARCH_LIMIT
): Promise<SearchResponse> {
  return fetchAPI<SearchResponse>("/search/image", {
    method: "POST",
    body: JSON.stringify({ image, limit }),
  });
}

// ─── Product Detail ─────────────────────────────────────────────────

export async function getProduct(id: number): Promise<Product> {
  return fetchAPI<Product>(`/products/${id}`);
}

// ─── Filters (dynamic from database) ────────────────────────────────

export async function getFilters(): Promise<FilterOptions> {
  return fetchAPI<FilterOptions>("/filters");
}

// ─── Product Bridges ───────────────────────────────────────────────

export async function getProductBridges(
  productId: number,
  opts?: { connection_mode?: string; min_score?: number; limit?: number; offset?: number }
): Promise<BridgeListResponse> {
  const params = new URLSearchParams();
  if (opts?.connection_mode) params.set("connection_mode", opts.connection_mode);
  if (opts?.min_score) params.set("min_score", String(opts.min_score));
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.offset) params.set("offset", String(opts.offset));
  const qs = params.toString();
  return fetchAPI<BridgeListResponse>(`/products/${productId}/bridges${qs ? `?${qs}` : ""}`);
}

export async function getStyleAncestry(
  productId: number,
  opts?: { min_score?: number; limit?: number; offset?: number }
): Promise<BridgeListResponse> {
  const params = new URLSearchParams();
  if (opts?.min_score) params.set("min_score", String(opts.min_score));
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.offset) params.set("offset", String(opts.offset));
  const qs = params.toString();
  return fetchAPI<BridgeListResponse>(`/products/${productId}/style-ancestry${qs ? `?${qs}` : ""}`);
}

export async function getStyleSiblings(
  productId: number,
  opts?: { min_score?: number; limit?: number; offset?: number }
): Promise<BridgeListResponse> {
  const params = new URLSearchParams();
  if (opts?.min_score) params.set("min_score", String(opts.min_score));
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.offset) params.set("offset", String(opts.offset));
  const qs = params.toString();
  return fetchAPI<BridgeListResponse>(`/products/${productId}/style-siblings${qs ? `?${qs}` : ""}`);
}

// ─── Global Bridges ────────────────────────────────────────────────

export async function getTopBridges(
  opts?: {
    connection_mode?: string;
    crossing_type?: string;
    min_score?: number;
    max_score?: number;
    min_year_gap?: number;
    directed?: boolean;
    sort?: string;
    limit?: number;
    offset?: number;
  }
): Promise<BridgeListResponse> {
  const params = new URLSearchParams();
  if (opts?.connection_mode) params.set("connection_mode", opts.connection_mode);
  if (opts?.crossing_type) params.set("crossing_type", opts.crossing_type);
  if (opts?.min_score) params.set("min_score", String(opts.min_score));
  if (opts?.max_score) params.set("max_score", String(opts.max_score));
  if (opts?.min_year_gap) params.set("min_year_gap", String(opts.min_year_gap));
  if (opts?.directed !== undefined) params.set("directed", String(opts.directed));
  if (opts?.sort) params.set("sort", opts.sort);
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.offset) params.set("offset", String(opts.offset));

  const qs = params.toString();
  return fetchAPI<BridgeListResponse>(`/bridges/top${qs ? `?${qs}` : ""}`);
}

export async function getBridgeStats(): Promise<BridgeStats> {
  return fetchAPI<BridgeStats>("/bridges/stats");
}

export async function getBridgeBetween(a: number, b: number): Promise<BridgeResult> {
  return fetchAPI<BridgeResult>(`/bridges/between/${a}/${b}`);
}

export async function getBridgeDetail(bridgeId: number): Promise<BridgeResult> {
  return fetchAPI<BridgeResult>(`/bridges/${bridgeId}`);
}

// ─── Explore ────────────────────────────────────────────────────

export async function getExploreFunctions(): Promise<FunctionListResponse> {
  return fetchAPI<FunctionListResponse>("/explore/functions");
}

export async function getExploreFunction(
  fn: string,
  opts?: { culture?: string; era?: string; limit?: number; offset?: number }
): Promise<FunctionDetailResponse> {
  const params = new URLSearchParams();
  if (opts?.culture) params.set("culture", opts.culture);
  if (opts?.era) params.set("era", opts.era);
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.offset) params.set("offset", String(opts.offset));
  const qs = params.toString();
  return fetchAPI<FunctionDetailResponse>(
    `/explore/functions/${encodeURIComponent(fn)}${qs ? `?${qs}` : ""}`
  );
}