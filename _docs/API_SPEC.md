# Vintage Vestige — API Specification

**As of: 2026-03-07**
**Status: All 16 endpoints implemented**

---

## Status Summary

| Endpoint | Status | Router | Schema |
|----------|--------|--------|--------|
| `POST /search/text` | **IMPLEMENTED** | search.py | TextSearchRequest → SearchResponse |
| `POST /search/image` | **IMPLEMENTED** | search.py | ImageSearchRequest → SearchResponse |
| `GET /products/{id}` | **IMPLEMENTED** | products.py | → ProductDetail |
| `GET /products/{id}/bridges` | **IMPLEMENTED** | products.py | → BridgeListResponse |
| `GET /products/{id}/modern-echoes` | **IMPLEMENTED** | products.py | → BridgeListResponse |
| `GET /products/{id}/style-ancestry` | **IMPLEMENTED** | products.py | → BridgeListResponse |
| `GET /products/{id}/style-siblings` | **IMPLEMENTED** | products.py | → BridgeListResponse |
| `GET /bridges/top` | **UPDATED** | bridges.py | → BridgeListResponse (+ 6 dimension filters + shared_function) |
| `GET /bridges/stats` | **IMPLEMENTED** | bridges.py | → BridgeStats |
| `GET /bridges/between/{a}/{b}` | **IMPLEMENTED** | bridges.py | → BridgeResult |
| `GET /bridges/{id}` | **IMPLEMENTED** | bridges.py | → BridgeResult |
| `GET /explore/functions` | **NEW** | explore.py | → FunctionListResponse |
| `GET /explore/functions/{function}` | **NEW** | explore.py | → FunctionDetailResponse |
| `GET /filters` | **IMPLEMENTED** | filters.py | → FilterOptions |
| `GET /health` | **IMPLEMENTED** | main.py | → {"status": "ok"} |

**Run:** `venv/bin/uvicorn api.main:app --reload`
**Docs:** `http://localhost:8000/docs` (Swagger) or `/redoc` (ReDoc)

---

## Schemas (13 total)

### api/schemas/product.py

- **ProductSummary** — 13 fields, compact product for bridge results. `from_attributes=True`.
- **ProductDetail** — 34 fields, full product for detail page. `from_attributes=True`. JSON TEXT fields parsed by `@field_validator`.

### api/schemas/search.py

- **SearchFilters** — 8 optional fields: era, decade, garment_type, vibe, occasion, fit_style, culture, material. Aligned 1:1 with FilterOptions.
- **TextSearchRequest** — query (str), limit (int, 1-100, default 12), filters (SearchFilters | None)
- **ImageSearchRequest** — image (str, base64 data URL), limit (int, 1-100, default 12)
- **SearchResult** — 18 fields (id, score, title, category, primary_image, enrichment fields)
- **SearchResponse** — results (list[SearchResult]), query (str), total (int)

### api/schemas/bridge.py

- **BridgeResult** — 17 fields, embeds ProductSummary for source/target. Includes 6 classification fields: temporal_type, crossing_type, connection_mode, primary_axis, secondary_axis, contrast_pair
- **BridgeListResponse** — bridges, total, limit, offset
- **BridgeTypeStats** — bridge_type, count, avg_score, min_score, max_score
- **ScoreHistogramBucket** — bucket (str), count (int)
- **BridgeStats** — total_bridges, total_products_with_bridges, by_type, score_histogram

### api/schemas/explore.py

- **FunctionSummary** — function (str), count (int)
- **FunctionListResponse** — functions (list[FunctionSummary]), total (int)
- **FunctionDetailResponse** — function (str), products (list[ProductSummary]), total, limit, offset

### api/schemas/filters.py

- **FilterOptions** — 8 list fields: eras, decades, vibes, garment_types, occasions, fit_styles, cultures, materials

---

## Endpoints

### Search

#### `POST /search/text`

Text-based semantic search with optional SQL filtering via pgvector.

**Request:**
```json
{
  "query": "dark academia Victorian dress",
  "limit": 12,
  "filters": {
    "era": "Victorian",
    "garment_type": "dress"
  }
}
```

**Implementation:**
1. Generate 384-dim embedding via `EmbeddingGenerator.generate_text_embedding(query)`
2. Build filter dict from non-null SearchFilters fields → SQL WHERE clauses
3. pgvector cosine distance search on `products.text_embedding` with HNSW index
4. Map SQL rows (product fields + similarity score) → SearchResult list

**Response:** SearchResponse

---

#### `POST /search/image`

Image-based semantic search using CLIP embeddings.

**Request:**
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQ...",
  "limit": 12
}
```

**Implementation:**
1. Split data URL on `,`, base64 decode → PIL Image
2. Generate 512-dim CLIP embedding via `EmbeddingGenerator.generate_image_embedding(pil_image)`
3. pgvector cosine distance search on `products.image_embedding` (no filters — ImageSearchRequest has no filters field)
4. Map SQL rows → SearchResult (same column set as text search)

**Response:** SearchResponse (query field = "[image]")

---

### Products

#### `GET /products/{product_id}`

Full product details with all enrichment fields.

**Implementation:** SQLAlchemy query → `ProductDetail.model_validate(product)` (JSON TEXT fields auto-parsed by field validators)

**Response:** ProductDetail

---

#### `GET /products/{product_id}/bridges`

Bridges involving a specific product.

**Query params:** bridge_type (optional), min_score (optional), limit (default 12), offset (default 0)

**Backend:** `bridge_queries.get_bridges_for_product()`

**Response:** BridgeListResponse

---

#### `GET /products/{product_id}/modern-echoes`

For pre-2000 items, find their post-2000 counterparts.

**Query params:** min_score (optional), limit (default 12), offset (default 0)

**Backend:** `bridge_queries.get_modern_echoes()`

**Response:** BridgeListResponse

---

#### `GET /products/{product_id}/style-ancestry`

For post-2000 items, find their pre-2000 ancestors.

**Query params:** min_score (optional), limit (default 12), offset (default 0)

**Backend:** `bridge_queries.get_style_ancestry()`

**Response:** BridgeListResponse

---

#### `GET /products/{product_id}/style-siblings`

Items with most shared structural attributes.

**Query params:** min_score (optional), limit (default 12), offset (default 0)

**Backend:** `bridge_queries.get_style_siblings()`

**Response:** BridgeListResponse

---

### Bridges

#### `GET /bridges/top`

Top-scoring bridges globally with optional filters.

**Query params:** bridge_type, min_score, max_score, source_platform, target_platform, temporal_type, crossing_type, connection_mode, primary_axis, shared_function, limit (default 20), offset (default 0)

**New dimension filters (2026-03-07):**
- `temporal_type` — transmission | continuation | contemporary
- `crossing_type` — same_context | cross_category | cross_culture | cross_category_culture
- `connection_mode` — contrast | resonance | affinity
- `primary_axis` — volume | ornament | body | register
- `shared_function` — filter bridges where both products share this social function (jsonb containment on `shared_attributes`)

**Backend:** `bridge_queries.get_top_bridges()`

**Response:** BridgeListResponse

---

#### `GET /bridges/stats`

Aggregate bridge statistics.

**Backend:** `bridge_queries.get_bridge_stats()`

**Response:** BridgeStats

---

#### `GET /bridges/between/{a}/{b}`

Check if a bridge exists between two specific products.

**Backend:** `bridge_queries.get_bridge_between()` (handles canonical ordering internally)

**Response:** BridgeResult or 404

---

#### `GET /bridges/{bridge_id}`

Get a single bridge with full product context.

**Backend:** `bridge_queries.get_bridge_detail()`

**Response:** BridgeResult or 404

---

### Explore

#### `GET /explore/functions`

List all social functions with product counts. Used for the function landing page.

**Backend:** `product_queries.get_all_social_functions()` — uses `jsonb_array_elements_text` to unnest JSON arrays.

**Response:** FunctionListResponse
```json
{
  "functions": [
    {"function": "wedding", "count": 142},
    {"function": "status-signaling", "count": 98}
  ],
  "total": 25
}
```

---

#### `GET /explore/functions/{function}`

Products matching a social function, filterable by culture and era.

**Query params:** culture (optional), era (optional), limit (default 50), offset (default 0)

**Backend:** `product_queries.get_products_by_function()` — uses `social_function::jsonb @> :fn_json` containment.

**Response:** FunctionDetailResponse (function name + paginated ProductSummary list)

---

### Filters

#### `GET /filters`

Available filter options for the search UI. Values dynamically queried from the products table.

**Implementation:** 8 SELECT DISTINCT queries, one per filter dimension.

**Response:** FilterOptions

---

## Dependencies

| Dependency | Provider | Used By |
|------------|----------|---------|
| Database session | `storage.database.get_db()` | products.py, bridges.py, filters.py, search.py (via VectorSearch) |
| VectorSearch (per-request) | `api.dependencies.get_vector_search(db)` | search.py — wraps pgvector queries, shares request DB session |
| EmbeddingGenerator (singleton) | `api.dependencies.get_embedding_generator()` | search.py — lru_cache(maxsize=1) |

---

## Frontend API Client (Complete)

The frontend API client at [vv-web/src/lib/api.ts](../vv-web/src/lib/api.ts) implements all endpoints:

```typescript
fetchAPI<T>(endpoint, options?)              // Generic fetch wrapper
searchByText(query, filters?, limit)         // POST /search/text
searchByImage(image, limit)                  // POST /search/image
getProduct(id)                               // GET /products/{id}
getFilters()                                 // GET /filters
getProductBridges(id, opts?)                 // GET /products/{id}/bridges
getModernEchoes(id, opts?)                   // GET /products/{id}/modern-echoes
getStyleAncestry(id, opts?)                  // GET /products/{id}/style-ancestry
getStyleSiblings(id, opts?)                  // GET /products/{id}/style-siblings
getTopBridges(opts?)                         // GET /bridges/top
getBridgeStats()                             // GET /bridges/stats
getBridgeBetween(a, b)                       // GET /bridges/between/{a}/{b}
getBridgeDetail(id)                          // GET /bridges/{id}
```
