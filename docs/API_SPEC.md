# Vintage Vestige — API Specification

**As of: 2026-02-22 (end of day)**
**Status: All 13 endpoints implemented**

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
| `GET /bridges/top` | **IMPLEMENTED** | bridges.py | → BridgeListResponse |
| `GET /bridges/stats` | **IMPLEMENTED** | bridges.py | → BridgeStats |
| `GET /bridges/between/{a}/{b}` | **IMPLEMENTED** | bridges.py | → BridgeResult |
| `GET /bridges/{id}` | **IMPLEMENTED** | bridges.py | → BridgeResult |
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

- **BridgeResult** — 11 fields, embeds ProductSummary for source/target
- **BridgeListResponse** — bridges, total, limit, offset
- **BridgeTypeStats** — bridge_type, count, avg_score, min_score, max_score
- **ScoreHistogramBucket** — bucket (str), count (int)
- **BridgeStats** — total_bridges, total_products_with_bridges, by_type, score_histogram

### api/schemas/filters.py

- **FilterOptions** — 8 list fields: eras, decades, vibes, garment_types, occasions, fit_styles, cultures, materials

---

## Endpoints

### Search

#### `POST /search/text`

Text-based semantic search with optional Qdrant pre-filtering.

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
2. Build `qdrant_client.models.Filter` from non-null SearchFilters fields
3. Search `vintage_text` collection with `query_filter` (native Qdrant pre-filtering)
4. Map Qdrant hits (dicts with score + payload) → SearchResult list

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
3. Search `vintage_images` collection (no filters — ImageSearchRequest has no filters field)
4. Map hits → SearchResult (same mapping as text search; both collections have identical payloads)

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

**Query params:** bridge_type, min_score, max_score, source_platform, target_platform, limit (default 20), offset (default 0)

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

### Filters

#### `GET /filters`

Available filter options for the search UI. Values dynamically queried from the products table.

**Implementation:** 8 SELECT DISTINCT queries, one per filter dimension.

**Response:** FilterOptions

---

## Dependencies

| Dependency | Provider | Used By |
|------------|----------|---------|
| Database session | `storage.database.get_db()` | products.py, bridges.py, filters.py |
| VectorDB singleton | `api.dependencies.get_vector_db()` | search.py |
| EmbeddingGenerator singleton | `api.dependencies.get_embedding_generator()` | search.py |

---

## Frontend API Client (Existing)

The frontend API client at [vv-web/src/lib/api.ts](../vv-web/src/lib/api.ts) already implements:

```typescript
fetchAPI<T>(endpoint, options?)       // Generic fetch wrapper
searchByText(query, filters?, limit)  // POST /search/text
searchByImage(image, limit)           // POST /search/image
getProduct(id)                        // GET /products/{id}
getFilters()                          // GET /filters
```

**Missing from frontend client:** All bridge endpoints (`/bridges/*`, `/products/*/bridges`, modern-echoes, style-ancestry, style-siblings).
