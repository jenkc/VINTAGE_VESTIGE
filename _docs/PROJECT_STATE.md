# Vintage Vestige — Project State

**As of: 2026-03-09**
**Audited by: Claude Code (codebase + live DB queries)**

---

## Executive Summary

Vintage Vestige is a fashion intelligence platform that connects vintage/historical garments with modern fashion through AI-enriched metadata and style bridges. The **data layer, intelligence layer, API layer, and frontend are all built and working**. All 4,234 products are enriched and embedded. **Bridge recomputation is in progress** — once complete, a new 6-dimensional bridge classifier will populate temporal_type, crossing_type, connection_mode, primary_axis, secondary_axis, and contrast_pair on every bridge. A new Social Function Explorer API enables browsing products by social function across eras and cultures. **Project reorganization** moved all scripts to `tools/` with only library code in package dirs, preparing for Docker deployment. Narrative generation overhauled with mode-specific prompts and classification context.

---

## Layer-by-Layer Status

### 1. Data Layer — WORKING

| Component | Status | Files | Lines |
|-----------|--------|-------|-------|
| Supabase PostgreSQL + pgvector ORM (Product, StyleBridge) | Working | [storage/database.py](storage/database.py) | ~133 |
| pgvector search module | Working | [storage/vector_search.py](storage/vector_search.py) | ~92 |
| Supabase Storage helper | Working | [storage/image_storage.py](storage/image_storage.py) | ~35 |
| Bridge query library | Working | [analysis/bridge_queries.py](analysis/bridge_queries.py) | 540 |
| Fashionpedia taxonomy | Working | [enrichment/fashionpedia_taxonomy.py](enrichment/fashionpedia_taxonomy.py) | 678 |
| Data loaders (Fashionpedia, Met, Smithsonian) | Working | [load_data/](load_data/) | ~4 scripts |

**Database state (Supabase, 2026-03-07):**
- `products` table: **4,234 rows** (va_museum: 1,856, fashionpedia: 1,000, smithsonian: 778, met_museum: 600)
- `style_bridges` table: **being recomputed** (`compute_bridges.py --rebuild` running)
- All products have HTTP URLs for images (Supabase Storage)
- **ALL 4,234 products enriched** with core_vibes and bridge_vibes
- **ALL 4,234 text embeddings** + **ALL 4,234 image embeddings** in pgvector columns
- StyleBridge has 6 new classification columns (pending classifier run)

**Vector storage:**
- `text_embedding vector(384)` column on products table (HNSW index, cosine)
- `image_embedding vector(512)` column on products table (HNSW index, cosine)
- No separate vector database — everything in Supabase PostgreSQL

### 2. Intelligence Layer — WORKING

| Component | Status | Files | Lines |
|-----------|--------|-------|-------|
| Claude enrichment (sync + async) | Working | [enrichment/claude.py](enrichment/claude.py) | 571 |
| Embedding generation (CLIP + MiniLM) | Working | [embeddings/generator.py](embeddings/generator.py), [embeddings/models.py](embeddings/models.py) | 275 |
| Bridge computation (2-pass) | Working | [tools/analysis/compute_bridges.py](tools/analysis/compute_bridges.py) | 615 |
| Bridge classification (6-dim) | Working | [tools/analysis/classify_bridge_dimensions.py](tools/analysis/classify_bridge_dimensions.py) | ~330 |
| Narrative generation (async) | **Overhauled** | [tools/analysis/generate_narratives.py](tools/analysis/generate_narratives.py) | 174 |
| Bridge HTML report | Working | [tests/data_integrity/bridge_report.py](tests/data_integrity/bridge_report.py) | 383 |

**Key facts:**
- Enrichment model: `claude-sonnet-4-20250514`
- Text embeddings: `all-MiniLM-L6-v2` (384-dim)
- Image embeddings: `clip-ViT-B-32` (512-dim)
- Bridge score: mode-dependent weights — contrast: `0.20*text + 0.20*image + 0.60*structural`, resonance: `0.60*text + 0.20*image + 0.20*structural`, affinity: `0.40*text + 0.30*image + 0.30*structural` (proportionally redistributed when image is NULL)
- **6-dimensional bridge classification**: temporal_type, crossing_type, connection_mode (contrast/resonance/affinity), primary_axis, secondary_axis, contrast_pair
- **9 opposition pairs** for contrast detection across 4 aesthetic axes (volume, ornament, body, register)
- Bridges being recomputed — narratives will be regenerated with full classification context (mode, temporal type, crossing type, axes, vibes)
- Narrative prompt overhauled: mode-specific system prompts, varied closings, formatted shared attributes, vibe data included
- Contrast bridges get 2 sentences / 60 words; others get 1 sentence / 40 words

### 3. API Layer — IMPLEMENTED

| Component | Status | Files | Details |
|-----------|--------|-------|---------|
| FastAPI main | Working | [api/main.py](api/main.py) | CORS, 5 router includes, /health |
| Dependencies | Working | [api/dependencies.py](api/dependencies.py) | get_vector_search, get_embedding_generator (Session-based + lru_cache) |
| Router: search | Working | [api/routers/search.py](api/routers/search.py) | POST /search/text (pgvector + SQL filters), POST /search/image (base64 + CLIP) |
| Router: products | Working | [api/routers/products.py](api/routers/products.py) | 5 endpoints (detail, bridges, modern-echoes, style-ancestry, style-siblings) |
| Router: bridges | Working | [api/routers/bridges.py](api/routers/bridges.py) | 4 endpoints (top with 6 dimension filters + shared_function, stats, between, detail) |
| Router: explore | **NEW** | [api/routers/explore.py](api/routers/explore.py) | 2 endpoints (list functions, function detail with culture/era filters) |
| Router: filters | Working | [api/routers/filters.py](api/routers/filters.py) | 1 endpoint (8 SELECT DISTINCT queries) |
| Schemas | Working | [api/schemas/](api/schemas/) | 16 Pydantic v2 models across 5 files + __init__.py |

**16 endpoints, 16 schemas.** Run with `venv/bin/uvicorn api.main:app --reload`. Auto-generated docs at `/docs` (Swagger) and `/redoc`.

### 4. Frontend Layer — COMPLETE

| Component | Status | Files |
|-----------|--------|-------|
| **Phase 1: Design System** | **DONE** | layout.tsx, tailwind.config.ts, globals.css, theme.ts, 4 UI primitives, next.config.ts |
| **Phase 2: Types & API** | **DONE** | types/index.ts (Product + 6 bridge types), api.ts (12 functions), constants.ts |
| **Phase 3A: Layout** | **DONE** | Header.tsx (sticky, mobile hamburger), Footer.tsx (3-col), root layout wired |
| **Phase 3B: Search** | **DONE** | SearchBar.tsx (debounced, 2 variants), ImageUpload.tsx (drag-drop + base64), ProductCard.tsx (image, badges, score) |
| **Phase 3C: Bridge components** | **DONE** | PlatformBadge, EraBadge, ScoreCircle, BridgeConnector, AttributePill, NarrativeBlock, ScoreBreakdown, BridgeCardFull, BridgeCardCompact, index.ts barrel |
| **Phase 3D: Utility components** | **DONE** | Skeleton.tsx (shimmer loader), ImageWithFallback.tsx (next/Image with gradient fallback) |
| **Phase 4: Pages** | **DONE** | Home (hero + how-it-works + featured bridges), Search (text search + filters + grid), Product detail (hero + ancestry + siblings), About |
| **Phase 5: Polish** | **DONE** | Error boundaries (global + page-level), loading states (home skeleton), SEO (generateMetadata, OG images), accessibility (aria-labels, roles, touch targets), scroll snap, ISR caching |

**Stack:** Next.js 16.1.6, React 19.2.3, Tailwind CSS 4, TypeScript 5, lucide-react icons.

**Build status:** `npx tsc --noEmit` and `npm run build` both pass clean. All 4 routes compile:
- `/` — static, revalidates every hour (ISR)
- `/about` — static
- `/search` — static (client-side data fetching)
- `/product/[id]` — dynamic (server-rendered per request)

**Not yet implemented:** Image search frontend (backend API exists at `POST /search/image`).

### 5. Testing — WORKING

| Component | Status | Files |
|-----------|--------|-------|
| Test configuration | Complete | [pyproject.toml](pyproject.toml), [tests/conftest.py](tests/conftest.py) |
| Unit tests | Complete | [tests/unit/](tests/unit/) (6 test files) |
| Integration tests | Complete | [tests/integration/](tests/integration/) (4 test files) |
| Data integrity tests | Complete | [tests/data_integrity/](tests/data_integrity/) (2 test files) |
| Search quality tests | Complete | [tests/search_quality/](tests/search_quality/) (1 test file) |

Unit tests need no external services; integration/data_integrity need Supabase PostgreSQL (pgvector).

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
| 4,234 products across 4 platforms | functional-hopping-barto.md | **Done** |
| Claude enrichment for all products | PHASE_1_IMPLEMENTATION.md | **Done** (4,234/4,234) |
| Embeddings for all products | PHASE_1_IMPLEMENTATION.md (Priority 1) | **Done** (4,234 text + 4,234 image) |
| StyleBridge model + compute pipeline | PHASE_1_IMPLEMENTATION.md (Priority 2-3) | **Recomputing** (`--rebuild` running) |
| 6-dimensional bridge classification | .claude/plans/zazzy-seeking-falcon.md | **Code done, pending run** (classifier + tests written) |
| Social Function Explorer API | docs/plans/FRONTEND_UPDATES.md | **Backend done** (2 new endpoints + shared_function filter) |
| Narrative generation for bridges | PHASE_1_IMPLEMENTATION.md (Priority 4) | **Overhauled** (prompt rewritten with classification context, pending bridge recomputation) |
| Bridge query utilities | PHASE_1_IMPLEMENTATION.md (Priority 5) | **Done** (bridge_queries.py, now with 6 dimension filters) |
| FastAPI endpoints | PHASE_1_IMPLEMENTATION.md (Priority 6) | **Done** (16 endpoints, 16 schemas) |
| Next.js frontend | PHASE_1_IMPLEMENTATION.md (Priority 7) | **Complete** (all 5 phases done, build passes, 4 routes compile) |
| Frontend updates (explorer, bridge badges) | docs/plans/FRONTEND_UPDATES.md | **Planned** |
| Supabase migration | .claude/plans/zazzy-seeking-falcon.md | **Complete** (all 20 steps done 2026-03-05) |
| Knowledge Graph | docs/plans/KG_IMPLEMENTATION/ | **Planned** (6 phase docs, prerequisites partly done) |
| Project reorganization (scripts → tools/) | .claude/plans/playful-crunching-stardust.md | **Phase 2 done** (scripts moved, tests passing; Phases 3-5 remaining) |
| Deployment (Railway + Vercel) | implement_full_plan.md (Week 3) | **Not started** |
| IIT 4.0 integration | IIT_4.0_INTEGRATION_PLAN.md | **Planned only** |
