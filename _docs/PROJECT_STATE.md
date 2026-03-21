# Vintage Vestige — Project State

**As of: 2026-03-20**
**Audited by: Claude Code (codebase + live DB queries)**

---

## Executive Summary

Vintage Vestige is a fashion intelligence platform that connects vintage/historical garments with modern fashion through AI-enriched metadata and entity-based style bridges. **Backend pipeline completely reworked (March 19-20).** All 4,234 products re-enriched with KG fields (designer, influences, movements, garment_system, material_origin, production_mode) and re-embedded with upgraded models (768d text + 768d image). **~24,000 entity-based bridges** computed via new 3-pass system (shared entities, lineage, visual echo). Frontend refactor in progress — 6-phase plan targeting deployment by April 10. See `_docs/FRONTEND_REFACTOR_PLAN.md`.

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

**Database state (Supabase, 2026-03-20):**
- `products` table: **4,234 rows** (va_museum: 1,856, fashionpedia: 1,000, smithsonian: 778, met_museum: 600)
- `style_bridges` table: **~24,000 bridges** (3 passes: shared_entity ~20,000, lineage ~1,020, visual_echo ~2,800)
- All products re-enriched with KG fields: designer, influence_references, named_movements, production_mode, material_origin, garment_system, display_title, low_confidence_fields
- 6-axis vibe_scores (Volume, Ornament, Exposure, Gender, Register, Occasion) on all products
- 61 V&A products have broken image URLs (no image embeddings)
- ~20 bridges have narratives (test batch — full generation pending API update)

**Vector storage:**
- `text_embedding vector(768)` — all-mpnet-base-v2 (HNSW index, cosine)
- `image_embedding vector(768)` — clip-ViT-L-14 (HNSW index, cosine)
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
- Enrichment model: `claude-sonnet-4-20250514` (cached system prompts)
- Text embeddings: `all-mpnet-base-v2` (768-dim)
- Image embeddings: `clip-ViT-L-14` (768-dim)
- **Entity-based bridge discovery** (`better_bridges.py`):
  - Pass 1: Shared Entities (inverted index, IDF scoring, entity multipliers, blocklist, rarity gate)
  - Pass 2: Lineage (directed, era parsing, embedding fallback, +5.0 lineage bonus)
  - Pass 3: Visual Echo (pgvector image similarity, batch commits, only unconnected pairs)
- Bridge score: `sigmoid(entity_score + context_score + embedding_bonus)` — entity-heavy
- Entity multipliers: designer(3.0), influence(2.5), movement(2.0), garment_system(1.5), construction(1.0), social_function(1.0), motif(0.75)
- Gates: MIN_ENTITY_SCORE=5.0 (8.0 same-era), MIN_ENTITY_IDF=2.0, BOUNDARY_YEAR_GAP=30, SAME_ERA_MAX_BRIDGES=300
- Narrative: one adaptive prompt, shared entities as substance, lineage direction noted
- **9 opposition pairs** for contrast detection across 4 aesthetic axes (volume, ornament, body, register)
- **Bridge narratives**: ALL 14,223 generated. Mode-specific system prompts, varied closings, vibe + classification context. Contrast: 2 sentences / 60 words; others: 1 sentence / 40 words

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
| Data integrity tests | Complete | [tests/data_integrity/](tests/data_integrity/) (3 test files — incl. new test_db_integrity.py with 35 tests) |
| Search quality tests | Complete | [tests/search_quality/](tests/search_quality/) (1 test file) |

**Full suite: 309 passed, 5 skipped, 0 failures** (run with `--ignore=tests/search_quality/old_tests`). Unit tests need no external services; integration/data_integrity need Supabase PostgreSQL (pgvector). The 5 skips are `test_database_model.py` in_memory_db tests (SQLite doesn't support pgvector ARRAY type).

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
| StyleBridge model + compute pipeline | PHASE_1_IMPLEMENTATION.md (Priority 2-3) | **Done** (14,223 bridges, 4-pass discovery, opposition sort, near-dup detection, same-era vibe gate) |
| 6-dimensional bridge classification | .claude/plans/zazzy-seeking-falcon.md | **Done** (14,194/14,223 classified; affinity 10,886 / contrast 3,314 / resonance 23) |
| Social Function Explorer API | docs/plans/FRONTEND_UPDATES.md | **Backend done** (2 new endpoints + shared_function filter) |
| Narrative generation for bridges | PHASE_1_IMPLEMENTATION.md (Priority 4) | **Done** (ALL 14,223 narratives generated; mode-specific prompts, classification context) |
| Bridge query utilities | PHASE_1_IMPLEMENTATION.md (Priority 5) | **Done** (bridge_queries.py, 6 dimension filters) |
| FastAPI endpoints | PHASE_1_IMPLEMENTATION.md (Priority 6) | **Done** (16 endpoints, 16 schemas) |
| Next.js frontend | PHASE_1_IMPLEMENTATION.md (Priority 7) | **Complete** (all 5 phases done, build passes, 4 routes compile) |
| Frontend updates (explorer, bridge badges) | docs/plans/FRONTEND_UPDATES.md | **Planned** |
| Supabase migration | .claude/plans/zazzy-seeking-falcon.md | **Complete** (all 20 steps done 2026-03-05) |
| Full test suite | — | **Done** (309 passed, 5 skipped, 0 failures as of 2026-03-13) |
| Knowledge Graph | docs/plans/KG_IMPLEMENTATION/ | **Planned** (all Phase 0 prerequisites now complete) |
| Project reorganization (scripts → tools/) | .claude/plans/playful-crunching-stardust.md | **Phase 2 done** (scripts moved, tests passing; Phases 3-5 remaining) |
| Deployment (Railway + Vercel) | implement_full_plan.md (Week 3) | **Not started** |
| IIT 4.0 integration | IIT_4.0_INTEGRATION_PLAN.md | **Planned only** |
