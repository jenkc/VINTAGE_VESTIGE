# Dev Diary: From Data Layer to Live API

**Project:** Vintage Vestige — a fashion intelligence platform that finds hidden connections between vintage garments across museums, archives, and marketplaces.

---

## Day 1 — February 21, 2026: The Schema Layer

### Starting Point

The data layer was complete: 866 products across three platforms (Fashionpedia, Met Museum, Smithsonian), enriched with AI-generated metadata, embedded into two Qdrant vector collections, and connected by 7,324 style bridges. The Next.js frontend was built and waiting. But between the data and the UI — nothing. The `api/` directory was a graveyard of broken stubs: an `__init__.py` containing just `=`, a `search.py` with syntax errors like `query = str` instead of `query: str`, and a `main.py` importing from paths that didn't exist.

Today's job: design the contract between backend and frontend.

### Designing 13 Schemas

Before writing a single endpoint, I defined every request and response shape as Pydantic v2 schemas. The process was archaeological — cross-referencing three sources of truth:

1. **TypedDict types** in `bridge_queries.py` (the data layer's output shape)
2. **TypeScript interfaces** in `vv-web/src/types/index.ts` (the frontend's expected input)
3. **SQLAlchemy ORM models** in `database.py` (the actual column definitions)

The schemas had to bridge all three. Thirteen models across four files:

- **product.py**: `ProductSummary` (13 fields, compact for bridge results) and `ProductDetail` (34 fields, full product page)
- **search.py**: `SearchFilters`, `TextSearchRequest`, `ImageSearchRequest`, `SearchResult`, `SearchResponse`
- **bridge.py**: `BridgeResult`, `BridgeListResponse`, `BridgeTypeStats`, `ScoreHistogramBucket`, `BridgeStats`
- **filters.py**: `FilterOptions` (8 filterable dimensions)

### The JSON-in-TEXT Problem

The ORM stores arrays like `style_tags` and `colors` as JSON strings in TEXT columns. The API needs actual arrays. A field validator handles the parsing:

```python
@field_validator("style_tags", "colors", mode="before")
@classmethod
def _parse_json_lists(cls, v):
    return _parse_json_list(v)
```

With `model_config = {"from_attributes": True}`, a single call like `ProductDetail.model_validate(orm_object)` handles everything — JSON parsing, type coercion, null defaults. No manual field mapping needed.

### Discovering Dead Columns

While cross-referencing the ORM model against actual data, I found five columns with zero rows populated out of 866: `color`, `season`, `year`, `pattern`, `period`. Leftovers from early dataset imports that were superseded by enrichment fields. Removed them from every schema before they could become permanent API baggage.

### Alignment

Caught that `SearchFilters` (what users send with search requests) and `FilterOptions` (what the `/filters` endpoint returns) were misaligned — different field names, different field counts. Aligned them to the same 8 dimensions: era, decade, garment_type, vibe, occasion, fit_style, culture, material. Now the filter dropdown options match exactly what the search accepts.

### Verification

All 13 schemas import cleanly. `ProductDetail.model_validate()` works with a live ORM object from Postgres. `BridgeResult.model_validate()` works with a TypedDict from `bridge_queries`. 100 unit tests pass (including 23 that were broken by a stale import path from an earlier directory restructure — fixed that too).

---

## Day 2 — February 22, 2026: Routers, Payloads, and a Working API

### Writing Routers By Hand

I made a deliberate choice to type every router by hand rather than have them generated. Slower, yes. But when I wrote `Depends(get_db)` for the tenth time, I actually understood what dependency injection was doing. When I accidentally shadowed an imported function name with an endpoint function name, I understood why Python resolved it the way it did.

**Products router** — five endpoints. The first draft had 30 lines of manual field mapping in `get_product`. Replaced it all with `ProductDetail.model_validate(product)`. One line. That's what the schema work on Day 1 was for.

**Bridges router** — four endpoints. Learned that route ordering matters: `/top`, `/stats`, and `/between/{a}/{b}` must be declared before `/{bridge_id}`, or FastAPI tries to parse "top" as an integer. Also learned that `bridge_queries` functions use keyword-only arguments (the `*` separator), so positional args silently fail.

**Filters router** — one endpoint, eight SELECT DISTINCT queries. Got four field names wrong on the first try (`Product.subcategory` instead of `Product.garment_type`, `Product.brand` instead of `Product.fit_style`). The ORM model is the source of truth, not my memory.

**Search router** — the most complex. Two POST endpoints (text and image), native Qdrant filtering, and a base64 image decoder.

### Native Qdrant Filtering

For text search, I wanted filters to happen at the vector database level, not in Python after fetching results. Added a `query_filter` parameter to `search_similar()` in the vector DB layer, then built a helper that converts the `SearchFilters` schema into Qdrant's native `Filter` format:

```python
def _build_qdrant_filter(filters: SearchFilters | None) -> Filter | None:
    if not filters:
        return None
    conditions = []
    for field, value in filters.model_dump(exclude_none=True).items():
        conditions.append(FieldCondition(key=field, match=MatchValue(value=value)))
    return Filter(must=conditions) if conditions else None
```

Clean, generic, and it means Qdrant prunes the search space before doing vector comparisons.

### The Payload Gap

The most interesting problem was discovering that the two Qdrant collections had different payload shapes. `vintage_text` had 28 metadata fields (all the enrichment data). `vintage_images` only had 12 — because the image embedding script was written as a gap-filler that ran after the enrichment pipeline, and nobody thought to include the enrichment fields in the payload.

This mattered because image search results would be missing material, vibe, garment_type, and everything else the frontend needs to display. Two options: join with Postgres on every image search, or fix the payloads at the source.

Wrote a backfill script using Qdrant's `set_payload()` — it merges new fields into existing points without touching the vectors. CLIP embeddings are computed from pixel data, so they don't care about metadata. All 866 points updated in seconds. Also fixed the image embedding script so future runs include the full payload by default. Both collections now have identical shapes.

### main.py

After all that, `main.py` was anticlimactic:

```python
app = FastAPI(title="Vintage Vestige API", version="1.0.0")

app.include_router(search.router)
app.include_router(products.router)
app.include_router(filters.router)
app.include_router(bridges.router)
```

That's basically it. All the complexity lives in the routers and schemas. The entry point just wires them together.

### The Final Count

```
api/
├── main.py              (22 lines)
├── dependencies.py      (singletons for Qdrant + embeddings)
├── schemas/             (13 Pydantic models)
│   ├── product.py       (ProductSummary, ProductDetail)
│   ├── search.py        (SearchFilters, TextSearchRequest, ImageSearchRequest, SearchResult, SearchResponse)
│   ├── bridge.py        (BridgeResult, BridgeListResponse, BridgeTypeStats, ScoreHistogramBucket, BridgeStats)
│   └── filters.py       (FilterOptions)
└── routers/             (13 endpoints)
    ├── search.py        (POST /search/text, POST /search/image)
    ├── products.py      (5 GET endpoints)
    ├── bridges.py       (4 GET endpoints)
    └── filters.py       (GET /filters)
```

13 schemas. 13 endpoints. Two days. Zero lines of code I don't understand.

### What I Learned

The biggest lesson across both days: **the shape of your data matters more than the code that moves it**. Day 1 was all schemas — no endpoints, no routes, just defining the contract. Day 2 the routers practically wrote themselves, because every question about "what fields do I return?" was already answered.

The payload gap was a bonus lesson: when two systems (text embeddings and image embeddings) are built by different scripts at different times, their data shapes drift. The fix was trivial, but only because I noticed it before building workarounds into the API layer.

Next up: running the test suite, then connecting the frontend to the live API.
