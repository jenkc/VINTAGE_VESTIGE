# Vintage Vestige — Session Handoff Document

**Last updated: 2026-02-23**
**Read this first in any new Claude Code session.**

---

## Session Log: 2026-02-23 — Figma Design Capture + Frontend Implementation Plan

### What Was Accomplished

**Figma Design Population:**
- Created 5 standalone HTML pages in `figma-pages/` that visually match the design handoff (`docs/FIGMA_DESIGN_HANDOFF.md`)
- Served pages via Python HTTP server on port 8888
- Captured all 5 into Figma file `3AXCKfChPdugtQOQ5629BP` using `generate_figma_design` MCP tool
- Files created:
  - `figma-pages/design-system.html` — Color swatches, typography scale, spacing, radii, shadows
  - `figma-pages/components.html` — All UI components (badges, cards, search, buttons, layout)
  - `figma-pages/home-desktop.html` — Full home page at 1440px
  - `figma-pages/search-results-desktop.html` — Search results with 4-col product grid
  - `figma-pages/product-detail-desktop.html` — Product hero + bridge sections

**Frontend Implementation Plan:**
- Explored all 14 FastAPI backend endpoints and Pydantic schemas
- Explored all existing Next.js frontend files (types, API client, components, stubs)
- Created comprehensive mobile-first implementation plan: `docs/plans/FRONTEND_IMPLEMENTATION_PLAN.md`
- Plan covers 5 phases, 41 files (13 modify, 6 populate, 22 create), with checklists and deliverables
- **User will implement this plan themselves** — not Claude

### Decisions Made

| Decision | Why |
|----------|-----|
| Mobile-first design (390px base) | Primary audience is Gen Z / younger Millennials on phones |
| Cormorant Garamond replaces Playfair Display | Per Figma design handoff — more editorial, vintage-appropriate |
| New color tokens replace `vintage.*` namespace | Handoff specifies specific palette (terracotta, gold, sage, platform colors, score colors) |
| BridgeCardFull: stacked on mobile, side-by-side on desktop | Images need to be large enough to see detail on small screens |
| BridgeCardCompact: 240px mobile, 280px desktop | 240px allows peek effect in carousel (1.5 cards visible at 390px) |
| No code implementation by Claude | User explicitly said "i was going to do the implementation. i just need the plan" |

### Files Created This Session

| File | Purpose |
|------|---------|
| `figma-pages/design-system.html` | Design system showcase for Figma capture |
| `figma-pages/components.html` | Component library showcase for Figma capture |
| `figma-pages/home-desktop.html` | Home page mock for Figma capture |
| `figma-pages/search-results-desktop.html` | Search results mock for Figma capture |
| `figma-pages/product-detail-desktop.html` | Product detail mock for Figma capture |
| `docs/plans/FRONTEND_IMPLEMENTATION_PLAN.md` | 5-phase mobile-first frontend implementation plan |

### Files Read But Not Modified

- `docs/FIGMA_DESIGN_HANDOFF.md` — Design tokens, components, page layouts
- `vv-web/src/lib/api.ts` — 4 existing API functions
- `vv-web/src/types/index.ts` — Product, SearchFilters, SearchResult types
- `vv-web/src/app/layout.tsx` — Playfair Display + Inter fonts
- `vv-web/tailwind.config.ts` — vintage.* color palette
- `vv-web/src/app/globals.css` — Base styles with vintage-* classes
- `vv-web/next.config.ts` — Empty config
- All existing component stubs in `vv-web/src/components/`

### What's Left Open

- **Frontend implementation** — User is doing this themselves using the plan doc
- **Figma refinement** — User said they're still refining the design
- **Bridge narratives** — Still 22/7,324 generated (needs `analysis/generate_narratives.py` run)
- **API smoke testing** — Endpoints still not tested against live services

---

## Session Log: 2026-02-21 + 2026-02-22 — FastAPI Backend Implementation

### What Was Accomplished

**Schemas (Day 1 — Feb 21):**
- Created `api/schemas/product.py` — `ProductSummary` (13 fields), `ProductDetail` (34 fields), `_parse_json_list()` helper
- Rewrote `api/schemas/search.py` — fixed syntax bugs, created `SearchFilters`, `TextSearchRequest`, `ImageSearchRequest`, `SearchResult`, `SearchResponse`
- Created `api/schemas/bridge.py` — `BridgeResult`, `BridgeListResponse`, `BridgeTypeStats`, `ScoreHistogramBucket`, `BridgeStats`
- Created `api/schemas/filters.py` — `FilterOptions` (8 list fields)
- Created `api/schemas/__init__.py` — re-exports all 13 schemas
- Fixed `api/__init__.py` — replaced broken `=` with empty file
- Fixed `tests/unit/test_bridge_logic.py` — updated stale import `scripts.analysis.compute_bridges` → `analysis.compute_bridges`

**Routers (Day 2 — Feb 22):**
- Wrote `api/routers/products.py` — 5 endpoints (get_product, product_bridges, modern_echoes, style_ancestry, style_siblings)
- Wrote `api/routers/bridges.py` — 4 endpoints (top_bridges, bridge_stats, bridge_between, bridge_detail)
- Wrote `api/routers/filters.py` — 1 endpoint (get_filters with 8 SELECT DISTINCT queries)
- Wrote `api/routers/search.py` — 2 endpoints (search_text with Qdrant filtering, search_image with base64 decode + CLIP)
- Wrote `api/dependencies.py` — `get_vector_db()` and `get_embedding_generator()` with `@lru_cache`
- Wrote `api/main.py` — FastAPI app wiring (CORS, 4 router includes, health endpoint)

**Infrastructure (Day 2 — Feb 22):**
- Modified `storage/vector_db.py` — added `query_filter` param to `search_similar()` for native Qdrant filtering
- Created `embeddings/scripts/backfill_image_payloads.py` — backfilled `vintage_images` payloads from 12 → 28 fields using `set_payload()`
- Modified `embeddings/scripts/generate_image_embeddings.py` — imports `build_full_payload()` so future runs include full payload
- Ran backfill script — both Qdrant collections now have identical payload shapes

**Documentation (Day 2 — Feb 22):**
- Created `docs/blog_first_api.md` — dev diary covering both days

### Decisions Made

| Decision | Why |
|----------|-----|
| Aligned SearchFilters and FilterOptions to 8 identical fields | 1:1 mapping means filter dropdowns match exactly what search accepts |
| Removed 5 dead columns from all schemas (color, season, year, pattern, period) | 0/866 populated, superseded by enrichment fields |
| Native Qdrant filtering (Option B) over Python post-filtering | Cleaner, faster — Qdrant prunes before vector comparison |
| Backfilled vintage_images payloads instead of Postgres join in image search | Eliminates per-request DB join; both collections now identical |
| No lifespan function in main.py | Qdrant/embedding singletons handled by lru_cache in dependencies.py |
| No /api/v1 prefix on routes | Frontend calls endpoints directly (http://localhost:8000/search/text) |

### Problems Encountered

| Problem | Resolution |
|---------|------------|
| `api/__init__.py` contained just `=` | Replaced with empty file |
| `api/schemas/search.py` had syntax bugs (`query = str`) | Rewrote from scratch |
| `tests/unit/test_bridge_logic.py` stale import path | Fixed `scripts.analysis.compute_bridges` → `analysis.compute_bridges` |
| `vintage_images` had 12 payload fields vs 28 in `vintage_text` | Wrote backfill script using `set_payload()` — no re-embedding needed |
| Route ordering — `/{bridge_id}` would match `/top` | Put `/top`, `/stats`, `/between/{a}/{b}` before `/{bridge_id}` |
| Function name shadowing in bridges router | Renamed endpoint functions (e.g., `top_bridges` not `get_top_bridges`) |
| bridge_queries functions use keyword-only args (`*`) | Must pass named params, not positional |

### What's Left Open
- Tests not yet run against the live API (user was running tests at end of session)
- `embedded_at` column still only set for 200/866 products (tracking gap, not data gap)
- 22/7,324 bridge narratives generated (need to run `generate_narratives.py`)
- Frontend search components are still stubs

---

## Environment Setup

### Prerequisites

- **Docker Desktop** — must be running (Jen starts this manually before sessions)
- Python 3.13+ with venv
- Node.js 25+ with npm
- PostgreSQL (local, database: `vintage_vestige`)
- Qdrant (local, port 6333) — runs in Docker, **must be started manually**
- Anthropic API key (for Claude enrichment/narratives)

### Start Services

```bash
# Start PostgreSQL (if not running via Homebrew)
brew services start postgresql@16

# Start Qdrant (Docker or binary — must be running for tests and search)
# Docker:
docker run -p 6333:6333 qdrant/qdrant
# Or if installed locally, check how user runs it

# Verify services
psql -d vintage_vestige -c "SELECT COUNT(*) FROM products;"  # Should return 866
curl http://localhost:6333/collections                        # Should list vintage_text, vintage_images
```

### Python Environment

```bash
# Always use the venv — never system python
source venv/bin/activate
# Or reference directly:
venv/bin/python <script>
venv/bin/pytest tests/
```

### Environment Variables

File: `.env` (exists in project root)

```
DATABASE_URL=postgresql+psycopg://localhost/vintage_vestige
QDRANT_HOST=localhost
QDRANT_PORT=6333
ANTHROPIC_API_KEY=sk-ant-...  # Required for enrichment/narratives
```

### Frontend

```bash
cd vv-web
npm install    # First time only
npm run dev    # http://localhost:3000
```

### Run Tests

```bash
venv/bin/pytest tests/                    # Full suite (156 tests, ~43s)
venv/bin/pytest tests/unit/               # Unit only (no DB needed)
venv/bin/pytest tests/integration/        # Needs Postgres + Qdrant
venv/bin/pytest tests/data_integrity/     # Needs Postgres + Qdrant
venv/bin/pytest tests/search_quality/     # Needs Postgres + Qdrant
venv/bin/pytest -m "not slow"             # Skip slow tests
```

---

## Current State (2026-02-23)

### What Works

- **866 products** in Postgres across 3 platforms (fashionpedia 500, met_museum 200, smithsonian 166)
- **All 866 enriched** by Claude Sonnet 4 with 23 structured fields
- **All 866 in Qdrant** — vintage_text (384d, 28 payload fields) + vintage_images (512d, 28 payload fields)
- **7,324 style bridges** computed (5 types: same_era, cross_category, cross_era, near_era, cross_vibe)
- **Bridge query library** (`analysis/bridge_queries.py`) — paginated, typed, filter-ready
- **FastAPI backend COMPLETE** — 14 endpoints across 4 routers, 13 Pydantic schemas, native Qdrant filtering
- **156 tests passing** (unit, integration, data_integrity, search_quality)
- **Frontend scaffolded** — Next.js 16 app with layout, homepage, types, API client, UI primitives
- **Figma design populated** — 5 pages captured into Figma file (design system, components, home, search, product detail)
- **Frontend implementation plan** — 5-phase mobile-first plan at `docs/plans/FRONTEND_IMPLEMENTATION_PLAN.md`

### What's Incomplete

- **22/7,324 bridge narratives** generated — the other 7,302 need `analysis/generate_narratives.py` run (~$13, ~1hr)
- **`embedded_at` column** only set for 200/866 products (tracking gap — actual embeddings exist for all)
- **Frontend implementation** — User is building this using the plan doc (all components/pages still pending)
- **Theme file** — `vv-web/src/styles/theme.ts` is empty
- **API smoke testing** — endpoints written but not yet tested against live services
- **Figma design refinement** — User is still iterating on the design

### What's Not Started

- **Deployment** (Railway + Vercel)

---

## Key File Locations

### Core Data Layer
| File | Purpose | Lines |
|------|---------|-------|
| [storage/database.py](../storage/database.py) | Product + StyleBridge ORM models | 127 |
| [storage/vector_db.py](../storage/vector_db.py) | Qdrant client (2 collections) | 137 |
| [analysis/bridge_queries.py](../analysis/bridge_queries.py) | Bridge query functions (TypedDict returns) | 540 |

### Intelligence Layer
| File | Purpose | Lines |
|------|---------|-------|
| [enrichment/claude.py](../enrichment/claude.py) | ClaudeEnricher (sync + async, enrichment + narratives) | 571 |
| [enrichment/fashionpedia_taxonomy.py](../enrichment/fashionpedia_taxonomy.py) | Full Fashionpedia ontology (27 cat, 294 attr) | 678 |
| [embeddings/generator.py](../embeddings/generator.py) | EmbeddingGenerator (text + image) | 176 |
| [embeddings/models.py](../embeddings/models.py) | Singleton model loader (MiniLM + CLIP) | 99 |

### Scripts
| File | Purpose | Lines |
|------|---------|-------|
| [analysis/compute_bridges.py](../analysis/compute_bridges.py) | 3-pass bridge discovery | 615 |
| [analysis/generate_narratives.py](../analysis/generate_narratives.py) | Async narrative generation | 168 |
| [tests/data_integrity/bridge_report.py](../tests/data_integrity/bridge_report.py) | HTML bridge visualization | 383 |

### API (IMPLEMENTED)
| File | Purpose | Endpoints/Schemas |
|------|---------|-------------------|
| [api/main.py](../api/main.py) | FastAPI app entry point | CORS, 4 router includes, /health |
| [api/dependencies.py](../api/dependencies.py) | Singleton providers | get_vector_db, get_embedding_generator |
| [api/routers/search.py](../api/routers/search.py) | Search endpoints | POST /search/text, POST /search/image |
| [api/routers/products.py](../api/routers/products.py) | Product endpoints | GET /products/{id}, /bridges, /modern-echoes, /style-ancestry, /style-siblings |
| [api/routers/bridges.py](../api/routers/bridges.py) | Bridge endpoints | GET /bridges/top, /stats, /between/{a}/{b}, /{id} |
| [api/routers/filters.py](../api/routers/filters.py) | Filter endpoint | GET /filters |
| [api/schemas/](../api/schemas/) | Pydantic models | 13 schemas across 4 files + __init__.py |

### Frontend
| File | Purpose | Lines |
|------|---------|-------|
| [vv-web/src/app/page.tsx](../vv-web/src/app/page.tsx) | Homepage (hero + how it works) | 95 |
| [vv-web/src/app/layout.tsx](../vv-web/src/app/layout.tsx) | Root layout (fonts, metadata) | 36 |
| [vv-web/src/lib/api.ts](../vv-web/src/lib/api.ts) | API client (4 endpoints) | 58 |
| [vv-web/src/types/index.ts](../vv-web/src/types/index.ts) | TypeScript types (Product, Search, Filters) | 106 |

### Planning & Documentation
| File | Purpose |
|------|---------|
| [docs/plans/technical_plan.md](../docs/plans/technical_plan.md) | Strategic architecture + 4-phase roadmap |
| [docs/plans/PHASE_1_IMPLEMENTATION.md](../docs/plans/PHASE_1_IMPLEMENTATION.md) | Detailed 8-priority Phase 1 plan |
| [docs/plans/implement_full_plan.md](../docs/plans/implement_full_plan.md) | 5-week detailed plan |
| [docs/IIT_4.0_INTEGRATION_PLAN.md](../docs/IIT_4.0_INTEGRATION_PLAN.md) | IIT 4.0 integration design (78K words, post-MVP) |
| [docs/IIT_REFERENCE.md](../docs/IIT_REFERENCE.md) | IIT quick-reference with code examples |
| [docs/CNN_INTEGRATION_SUMMARY.md](../docs/CNN_INTEGRATION_SUMMARY.md) | CNN visual attribute extraction plan |
| [docs/reference/fashion_intelligence_platform.md](../docs/reference/fashion_intelligence_platform.md) | Product strategy (6 customer segments, 5-phase roadmap) |
| [docs/reference/cross_source_bridges.md](../docs/reference/cross_source_bridges.md) | Bridge system design document |
| [docs/reference/outreach_templates.md](../docs/reference/outreach_templates.md) | Email templates for museum/dataset partnerships |
| [docs/reference/vintage_databases.md](../docs/reference/vintage_databases.md) | Data source guide (museum APIs, scraping) |
| [docs/blog_bridge_system.md](../docs/blog_bridge_system.md) | Technical blog post about building bridges |

---

## Known Gotchas

1. **Always use `venv/bin/python`** — system Python won't have the packages.

2. **Qdrant must be running** for integration tests, data integrity tests, and any search functionality. It's not auto-started.

3. **`embedded_at` is misleading** — only 200/866 products have this timestamp, but all 866 are in Qdrant. Don't filter by `embedded_at IS NOT NULL` to find "embedded" products.

4. **Bridge canonical ordering** — `source_id < target_id` always. When looking up a bridge between products A and B, use `min(A,B)` as source and `max(A,B)` as target.

5. **`bridge_narrative` not `narrative`** — The column is `bridge_narrative`. Earlier code/docs may reference just `narrative`.

6. **Embedding model loading is slow** — First import of `embeddings.models` downloads ~500MB of model weights. Subsequent loads are cached.

7. **`vintage_images` payloads were backfilled** on 2026-02-22. Both collections now have 28 payload fields. No Postgres join needed for image search.

8. **JSON fields in Postgres** — `style_tags`, `colors`, `textile_finishing`, `garment_parts`, `decorations`, `image_urls` are all `Text` columns storing JSON strings, not JSONB. Parse with `json.loads()`.

9. **Score distribution is tight** — Fashion corpus items cluster closely in embedding space. The minimum bridge score threshold is 0.30 and the average is 0.556. Don't expect scores as spread out as general-purpose search.

10. **`generate_bridge_narrative` max_tokens=200** — Was 100 originally, caused truncation. If narratives are still truncating, increase this.

---

## Priorities for Next Session

### Immediate

1. **Finalize Figma design** — User is refining the design in Figma.

2. **Implement frontend** — Follow `docs/plans/FRONTEND_IMPLEMENTATION_PLAN.md` (5 phases, 41 files). User is doing this.

3. **Test the live API** — `venv/bin/uvicorn api.main:app --reload`, hit endpoints via /docs or curl. Fix any runtime issues.

4. **Run narrative generation** — `venv/bin/python analysis/generate_narratives.py` to populate all 7,324 bridge narratives (~$13, ~1hr).

5. **Fix `embedded_at` tracking** — One SQL update to backfill the 666 missing timestamps.

### Stretch (portfolio-ready)

6. **Deploy** — Backend to Railway, frontend to Vercel.
7. **Write case study** — Build on existing blog drafts (bridge system + first API).
8. **IIT 4.0** — Start with Approach 1 (Φ-Based Search Ranking) per the reference doc.
