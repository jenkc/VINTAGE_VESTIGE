# Vintage Vestige — Project State

**As of: 2026-02-25**
**Audited by: Claude Code (codebase + live DB queries)**

---

## Executive Summary

Vintage Vestige is a fashion intelligence platform that connects vintage/historical garments with modern fashion through AI-enriched metadata and style bridges. The **data layer, intelligence layer, and API layer are built and working**. The **frontend has layout, types, search components, and 7 of 10 bridge components built**. Deployment has not started.

---

## Layer-by-Layer Status

### 1. Data Layer — WORKING

| Component | Status | Files | Lines |
|-----------|--------|-------|-------|
| PostgreSQL ORM (Product, StyleBridge) | Working | [storage/database.py](storage/database.py) | 127 |
| Qdrant vector client | Working | [storage/vector_db.py](storage/vector_db.py) | 137 |
| Bridge query library | Working | [analysis/bridge_queries.py](analysis/bridge_queries.py) | 540 |
| Fashionpedia taxonomy | Working | [enrichment/fashionpedia_taxonomy.py](enrichment/fashionpedia_taxonomy.py) | 678 |
| Data loaders (Fashionpedia, Met, Smithsonian) | Working | [load_data/](load_data/) | ~4 scripts |

**Database state (live query 2026-02-22):**
- `products` table: **866 rows** (fashionpedia: 500, met_museum: 200, smithsonian: 166)
- `style_bridges` table: **7,324 rows** (5 types, scores 0.30–0.93)
- All 866 products enriched (`enriched_at IS NOT NULL`)
- All 866 have `embedded_at` set (backfilled 2026-02-22)

**Qdrant state (live query 2026-02-22):**
- `vintage_text`: 866 points, 384-dim, cosine, 21 payload fields including `platform` + `fp_category`
- `vintage_images`: 866 points, 512-dim, cosine, 28 payload fields (backfilled 2026-02-22 to match vintage_text)

### 2. Intelligence Layer — WORKING

| Component | Status | Files | Lines |
|-----------|--------|-------|-------|
| Claude enrichment (sync + async) | Working | [enrichment/claude.py](enrichment/claude.py) | 571 |
| Embedding generation (CLIP + MiniLM) | Working | [embeddings/generator.py](embeddings/generator.py), [embeddings/models.py](embeddings/models.py) | 275 |
| Bridge computation (3-pass) | Working | [analysis/compute_bridges.py](analysis/compute_bridges.py) | 615 |
| Narrative generation (async) | Working | [analysis/generate_narratives.py](analysis/generate_narratives.py) | 168 |
| Bridge HTML report | Working | [tests/data_integrity/bridge_report.py](tests/data_integrity/bridge_report.py) | 383 |

**Key facts:**
- Enrichment model: `claude-sonnet-4-20250514`
- Text embeddings: `all-MiniLM-L6-v2` (384-dim)
- Image embeddings: `clip-ViT-B-32` (512-dim)
- Bridge score: `0.40*text + 0.30*image + 0.30*structural` (with image), `0.55*text + 0.45*structural` (without)
- Only **22/7,324 bridges** have narratives generated (3 need to be batch-run)

### 3. API Layer — IMPLEMENTED

| Component | Status | Files | Details |
|-----------|--------|-------|---------|
| FastAPI main | Working | [api/main.py](api/main.py) | CORS, 4 router includes, /health |
| Dependencies | Working | [api/dependencies.py](api/dependencies.py) | get_vector_db, get_embedding_generator (lru_cache singletons) |
| Router: search | Working | [api/routers/search.py](api/routers/search.py) | POST /search/text (with Qdrant filters), POST /search/image (base64 + CLIP) |
| Router: products | Working | [api/routers/products.py](api/routers/products.py) | 5 endpoints (detail, bridges, modern-echoes, style-ancestry, style-siblings) |
| Router: bridges | Working | [api/routers/bridges.py](api/routers/bridges.py) | 4 endpoints (top, stats, between, detail) |
| Router: filters | Working | [api/routers/filters.py](api/routers/filters.py) | 1 endpoint (8 SELECT DISTINCT queries) |
| Schemas | Working | [api/schemas/](api/schemas/) | 13 Pydantic v2 models across 4 files + __init__.py |

**13 endpoints, 13 schemas.** Run with `venv/bin/uvicorn api.main:app --reload`. Auto-generated docs at `/docs` (Swagger) and `/redoc`.

### 4. Frontend Layer — IN PROGRESS (Phase 3C.8 next)

| Component | Status | Files |
|-----------|--------|-------|
| **Phase 1: Design System** | **DONE** | layout.tsx, tailwind.config.ts, globals.css, theme.ts, 4 UI primitives, next.config.ts |
| **Phase 2: Types & API** | **DONE** | types/index.ts (Product + 6 bridge types), api.ts (12 functions), constants.ts |
| **Phase 3A: Layout** | **DONE** | Header.tsx (sticky, mobile hamburger), Footer.tsx (3-col), root layout wired |
| **Phase 3B: Search** | **DONE** | SearchBar.tsx (debounced, 2 variants), ImageUpload.tsx (drag-drop + base64), ProductCard.tsx (image, badges, score) |
| **Phase 3C: Bridge components** | **7/10 DONE** | PlatformBadge, EraBadge, ScoreCircle, BridgeConnector, AttributePill, NarrativeBlock, ScoreBreakdown |
| **Phase 3C: Remaining** | **NEXT** | BridgeCardFull.tsx, BridgeCardCompact.tsx (empty stubs), index.ts barrel |
| Phase 3D: Utility components | Pending | Skeleton.tsx, ImageWithFallback.tsx |
| Phase 4: Pages | Pending | Home rebuild, Search, Product detail, About |
| Phase 5: Polish | Pending | Error boundaries, loading states, SEO, accessibility |

**Stack:** Next.js 16.1.6, React 19.2.3, Tailwind CSS 4, TypeScript 5, lucide-react icons.

**Design system aligned to Figma:** Cormorant Garamond serif, flat color tokens (terracotta, gold, sage, cream, charcoal), custom shadows/radii. All UI primitives updated. `npm run build` and `npx tsc --noEmit` pass clean.

**API client complete:** All 12 backend endpoints callable (4 search/product + 8 bridge functions). Types mirror backend Pydantic schemas exactly.

**Search components complete:** SearchBar (debounced, large/compact), ImageUpload (drag-drop, base64 conversion, preview), ProductCard (union type for SearchResult|ProductSummary, next/Image with fill, platform badge, era badge, match %).

**Bridge primitives complete (7/10):** PlatformBadge, EraBadge, ScoreCircle, BridgeConnector, AttributePill, NarrativeBlock, ScoreBreakdown. BridgeCardFull and BridgeCardCompact are empty stubs.

### 5. Testing — WORKING

| Component | Status | Files |
|-----------|--------|-------|
| Test configuration | Complete | [pyproject.toml](pyproject.toml), [tests/conftest.py](tests/conftest.py) |
| Unit tests | Complete | [tests/unit/](tests/unit/) (6 test files) |
| Integration tests | Complete | [tests/integration/](tests/integration/) (4 test files) |
| Data integrity tests | Complete | [tests/data_integrity/](tests/data_integrity/) (2 test files) |
| Search quality tests | Complete | [tests/search_quality/](tests/search_quality/) (1 test file) |

**156 tests, ~43s runtime.** Unit tests need no external services; integration/data_integrity need Postgres + Qdrant.

### 6. Scrapers — PARTIAL

| Component | Status | Files | Lines |
|-----------|--------|-------|-------|
| Base scraper (ABC) | Complete | [scrapers/base.py](scrapers/base.py) | 21 |
| Etsy scraper | Functional | [scrapers/etsy.py](scrapers/etsy.py) | 156 |
| Depop scraper | Mock/stub | [scrapers/depop.py](scrapers/depop.py) | 52 |

The Etsy scraper does real HTTP scraping with BeautifulSoup. Depop returns hardcoded test data. Neither is currently used in the main data pipeline (data comes from HuggingFace datasets and museum APIs).

### 7. Documentation & Planning — EXISTS

| Document | Location | Purpose |
|----------|----------|---------|
| Technical plan | [docs/plans/technical_plan.md](docs/plans/technical_plan.md) | Strategic architecture + 4-phase roadmap |
| Phase 1 implementation | [docs/plans/PHASE_1_IMPLEMENTATION.md](docs/plans/PHASE_1_IMPLEMENTATION.md) | Detailed 8-priority plan with code examples |
| Full implementation plan | [docs/plans/implement_full_plan.md](docs/plans/implement_full_plan.md) | 5-week plan (API → Frontend → Deploy → Blog → Outreach) |
| **Frontend implementation** | [docs/plans/FRONTEND_IMPLEMENTATION_PLAN.md](docs/plans/FRONTEND_IMPLEMENTATION_PLAN.md) | **5-phase mobile-first frontend plan (2026-02-23)** |
| **Figma design handoff** | [docs/FIGMA_DESIGN_HANDOFF.md](docs/FIGMA_DESIGN_HANDOFF.md) | **Design tokens, components, page layouts** |
| IIT 4.0 integration plan | [docs/IIT_4.0_INTEGRATION_PLAN.md](docs/IIT_4.0_INTEGRATION_PLAN.md) | Future: IIT-based consciousness metrics for bridges |
| CNN integration summary | [docs/CNN_INTEGRATION_SUMMARY.md](docs/CNN_INTEGRATION_SUMMARY.md) | Future: CNN visual attribute extraction |
| Blog draft (bridge system) | [docs/blog_bridge_system.md](docs/blog_bridge_system.md) | Technical blog post about building bridges |
| Architecture diagram | [docs/plans/architecture.html](docs/plans/architecture.html) | Visual system architecture |

---

## What the Plans Said vs. What's Real

| Plan Item | Planned In | Status |
|-----------|-----------|--------|
| 866 products across 3 platforms | technical_plan.md | **Done** |
| Claude enrichment for all products | PHASE_1_IMPLEMENTATION.md | **Done** (866/866) |
| Qdrant payloads with platform + fp_category | PHASE_1_IMPLEMENTATION.md (Priority 1) | **Done** |
| StyleBridge model + compute pipeline | PHASE_1_IMPLEMENTATION.md (Priority 2-3) | **Done** (7,324 bridges) |
| Narrative generation for bridges | PHASE_1_IMPLEMENTATION.md (Priority 4) | **Code done, only 22/7324 run** |
| Bridge query utilities | PHASE_1_IMPLEMENTATION.md (Priority 5) | **Done** (bridge_queries.py) |
| FastAPI endpoints | PHASE_1_IMPLEMENTATION.md (Priority 6) | **Done** (13 endpoints, 13 schemas, implemented 2026-02-21/22) |
| Next.js frontend | PHASE_1_IMPLEMENTATION.md (Priority 7) | **In progress** (Phases 1-3A done, 3B search done, 3C bridge 7/10 done; pages pending) |
| Figma design system | FIGMA_DESIGN_HANDOFF.md | **Populated in Figma** (5 pages captured 2026-02-23; user refining) |
| Frontend implementation plan | FRONTEND_IMPLEMENTATION_PLAN.md | **Complete** (5 phases, 41 files, mobile-first) |
| Deployment (Railway + Vercel) | implement_full_plan.md (Week 3) | **Not started** |
| Blog post + portfolio | implement_full_plan.md (Week 4) | **Draft exists** |
| IIT 4.0 integration | IIT_4.0_INTEGRATION_PLAN.md | **Planned only** (future epic) |
| CNN visual attributes | CNN_INTEGRATION_SUMMARY.md | **Planned only** (future epic) |
