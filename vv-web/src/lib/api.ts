import { API_BASE_URL, DEFAULT_SEARCH_LIMIT } from "./constants";
import type {
  SearchResponse,
  SearchFilters,
  FilterOptions,
  Product,
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
