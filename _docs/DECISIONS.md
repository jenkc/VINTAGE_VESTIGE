# Vintage Vestige — Key Decisions

**Last updated: 2026-03-20**

---

## Decision Log

### 2026-03-19/20: Entity-Based Bridges Replace Embedding-Similarity

**Decision:** Rewrote bridge computation from scratch. Old system found bridges via embedding similarity + vibe axis opposition. New system finds bridges via shared entities (designer, movement, technique, influence citations) with IDF-weighted scoring.

**Why:** After extensive testing, axis-based contrast ("these two garments disagree about volume") produced uninteresting results. Bridges are only interesting as *paths* — connections with a specific, nameable reason. Entity-based discovery provides that reason natively.

**Reversals:**
- 22 discrete vibes → 6 axes → axes kept for filtering but removed from bridge logic
- Opposition/contrast as a connection mode → dropped entirely
- `structural_score` as a component → replaced by `entity_score` (IDF-weighted)
- 6 mode-specific narrative prompts → 1 adaptive prompt

### 2026-03-19/20: Embedding Model Upgrades

**Decision:** Text: MiniLM (384d) → mpnet (768d). Image: CLIP ViT-B-32 (512d) → ViT-L-14 (768d).

**Why:** mpnet is significantly better at semantic similarity. ViT-L-14 catches fine-grained visual distinctions (silhouette subtleties, fabric texture). Both are drop-in replacements in sentence-transformers.

### 2026-03-19/20: Lineage Bridges Are Directed

**Decision:** Lineage bridges flow older → newer. Source = the original/tradition, target = the item referencing it.

**Why:** "This 2020 dress references 1890s leg-of-mutton sleeves" has a direction. The original is the source. Thread Pull follows these arrows to trace design lineage through history.

### 2026-03-19/20: IDF Scoring for Entity Importance

**Decision:** Entity values scored by inverse document frequency: `log(N/count)`. Rare entities (Japonisme, Perry Ellis) score high. Common entities (hand-sewing, everyday-practical) score near zero.

**Why:** Standard information retrieval approach. Two products sharing "Japonisme" (15 products) is a much stronger signal than sharing "hand-sewing" (1,279 products).

### 2026-03-19/20: Knowledge Graph Deferred

**Decision:** Full KG implementation deferred. Entity-based bridges are KG-ready but we're not building graph infrastructure now.

**Why:** Outside Jen's expertise, and entity-based bridges + Thread Pull deliver 80% of the KG value without the complexity. Can add later.

### 2026-03-19/20: Thread Pull as Signature Interaction

**Decision:** The "Thread Pull" — follow the graph from any garment — is the primary new interaction for the v2 frontend. Axis slider and opposition theater dropped.

**Why:** Axes don't produce interesting results. Thread Pull leverages entity-based bridges naturally — each step shows which shared entities connected the graph.

### 2026-03-19/20: 3-Week Deployment Target

**Decision:** Deploy by April 10. 6-phase frontend refactor plan.

**Why:** The backend is ready. Frontend needs to catch up to the new bridge schema. Aggressive but achievable with the detailed plan.

---

### 1. Dataset Approach: Museum APIs + HuggingFace vs. Scraping

**Date:** ~2026-02-15
**Context:** Need fashion items to populate the platform. Options: (a) scrape live marketplaces like Depop/Etsy, (b) use publicly available datasets and museum APIs, (c) hybrid.
**Decision:** Start with HuggingFace Fashionpedia dataset (500 items) + Met Museum API (200 items) + Smithsonian API (166 items). Scrapers exist but are not the primary data source.
**Rationale:**
- Museum APIs are free, reliable, and provide rich metadata (culture, period, object_date)
- Fashionpedia has expert-annotated taxonomy labels (27 categories, 294 attributes)
- No legal risk vs. scraping Depop/Etsy
- 866 items is enough to prove the intelligence layer
**Alternatives considered:** Etsy scraper built ([scrapers/etsy.py](../scrapers/etsy.py), 156 lines), Depop stub created; real-time scraping deferred to Phase 3
**Outcome:** 866 products across 3 platforms; all enriched and embedded
**Reference:** [docs/reference/vintage_databases.md](reference/vintage_databases.md)

---

### 2. AI Enrichment Strategy: Claude + Re-embed Enriched Text

**Date:** ~2026-02-15
**Context:** Raw product metadata from different sources is inconsistent. Museum records use archival language ("Evening dress, ca. 1865"); modern search uses aesthetic language ("dark academia"). Need a bridge.
**Decision:** Use Claude Sonnet 4 to enrich every product with 23 structured fields (12 Fashionpedia taxonomy + 11 creative/search-bridge fields), then build `enriched_text` from those fields and embed that instead of raw titles/descriptions.
**Rationale:**
- Single Claude call per product produces consistent structured metadata regardless of source
- Fashionpedia taxonomy gives standardized garment attributes
- Creative fields (vibe, style_tags, occasion) bridge historical items to modern search vocabulary
- Re-embedding enriched text means search works against rich, normalized content
**Alternatives considered:** Raw metadata embeddings only (poor cross-source retrieval); fine-tuning CLIP on fashion domain (expensive, deferred to IIT 4.0 Phase 2)
**Outcome:** 866/866 products enriched; enriched_text used for all text embeddings
**Cost:** ~$5-10 total for 866 enrichments

---

### 3. Embedding Models: all-MiniLM-L6-v2 + clip-ViT-B-32

**Date:** ~2026-02-15
**Context:** Need text and image embeddings for semantic search.
**Decision:** `all-MiniLM-L6-v2` (384-dim) for text, `clip-ViT-B-32` (512-dim) for images. Separate embedding columns on the products table (pgvector), not a joint embedding space.
**Rationale:**
- MiniLM is fast, small, and effective for short rich text (~256 tokens)
- CLIP handles both text and images but its text encoder is less effective for nuanced fashion descriptions than a dedicated text model
- Separate columns allow independent search and scoring
- SentenceTransformers provides both via a unified API
**Alternatives considered:** Joint CLIP space (text-image alignment but worse text quality); OpenAI embeddings (cost); BERT-large (overkill for short texts)
**Outcome:** Both models load via singleton pattern; ~500MB total download
**Trade-off:** No native cross-modal ranking — addressed by bridge scoring algorithm

---

### 4. Bridge System: 3-Pass Discovery with Canonical Ordering

**Date:** ~2026-02-19
**Context:** The core product differentiation is "style bridges" — connections between garments across eras and categories. Need to discover them at scale.
**Decision:** 2-pass pgvector search (open discovery, cross-culture) → composite scoring (text + image + structural) → canonical ordering (source_id < target_id) → unique constraint.
**Rationale:**
- Open discovery finds the obvious matches; cross-culture finds the interesting cross-cultural connections
**Updated:** 2026-03-06 — Reduced from 3 passes to 2 (cross-category pass removed as it produced redundant results)
- Composite scoring prevents text-only or image-only domination
- Canonical ordering prevents A→B and B→A duplicates (~15K → 7,324 bridges)
- Structural score based on Fashionpedia taxonomy gives explainable similarity
**Alternatives considered:** All-pairs comparison (O(n²) = 750K pairs, too slow); single-pass search (misses cross-category connections); text-only scoring (loses visual information)
**Outcome:** 7,324 bridges, 5 types, scores 0.30–0.93
**Lessons learned:** Self-bridges from old runs required data cleanup; bidirectional storage was caught late (see [docs/blog_bridge_system.md](blog_bridge_system.md))

---

### 5. Bridge Scoring Formula: 0.40 text + 0.30 image + 0.30 structural

**Date:** ~2026-02-19
**Context:** How to combine text similarity, image similarity, and structural overlap into a single bridge score.
**Decision:** Weighted average: 40% text + 30% image + 30% structural (with image); 55% text + 45% structural (without image).
**Rationale:**
- Text embeddings encode the richest information (enriched_text has 23 fields)
- Image similarity catches visual patterns that text misses
- Structural score (Fashionpedia taxonomy overlap) provides explainability
- When image is missing, text gets extra weight rather than penalizing the pair
**Alternatives considered:** Equal weighting (structural too noisy at 33%); text-only (misses visual connections); learned weights (not enough labeled data)
**Outcome:** Score distribution: avg 0.556, range 0.30–0.93; 2,243/7,324 have image similarity

---

### 6. Backend Framework: FastAPI (over Node/Express)

**Date:** ~2026-02-15
**Context:** Need a REST API to serve search results and bridge data to the frontend.
**Decision:** FastAPI with Pydantic schemas.
**Rationale:**
- Python backend means embedding models and database client can run in the same process
- FastAPI has async support for concurrent Claude calls
- Pydantic schemas provide automatic validation and OpenAPI docs
- Already using Python for the entire intelligence layer
**Alternatives considered:** Node.js/Express (would require Python microservice for embeddings); Django (too heavy); Flask (no async, no auto-docs)
**Outcome:** FastAPI implemented (v0.104.1) — 13 endpoints, 13 Pydantic schemas, 4 routers (2026-02-22)
**Reference:** [docs/plans/technical_plan.md](plans/technical_plan.md)

---

### 7. Frontend Framework: Next.js 16 + Tailwind

**Date:** ~2026-02-20
**Context:** Need a web frontend for the search experience.
**Decision:** Next.js 16 with React 19, TypeScript, Tailwind CSS 4.
**Rationale:**
- Next.js handles SSR/SSG for SEO (important for portfolio piece)
- React 19 with Server Components for performance
- Tailwind for rapid styling without custom CSS
- TypeScript for type safety matching backend schemas
**Alternatives considered:** Plain React (no SSR); Remix (less ecosystem); Svelte (smaller community)
**Outcome:** Project scaffolded, homepage renders, layout + types complete; functional search components not yet built

---

### 8. Fashionpedia Taxonomy as Structural Backbone

**Date:** ~2026-02-15
**Context:** Need a standardized vocabulary for garment attributes across museum and modern sources.
**Decision:** Adopt the Fashionpedia ontology (ECCV 2020) as the structural backbone: 27 main categories, 294 attributes across 9 supercategories.
**Rationale:**
- Only comprehensive fashion ontology that covers both historical and modern garments
- Provides standardized vocabulary: silhouette, neckline, waistline, etc.
- Enables structural scoring for bridges (Jaccard overlap on taxonomy fields)
- Expert-annotated labels from Fashionpedia dataset give ground truth for 500 items
**Alternatives considered:** Custom taxonomy (too much work); simple tags (no hierarchy); fashion-specific embeddings (no explainability)
**Outcome:** Full taxonomy implemented in [enrichment/fashionpedia_taxonomy.py](../enrichment/fashionpedia_taxonomy.py) (678 lines); Claude enrichment uses Fashionpedia categories as output schema
**Reference:** [docs/reference/cross_source_bridges.md](reference/cross_source_bridges.md)

---

### 9. IIT 4.0 as Future Epic (Not MVP)

**Date:** 2026-02-19
**Context:** Integrated Information Theory could improve search ranking by measuring cross-modal information integration (Φ). Designed as 4 approaches spanning 6-10 weeks.
**Decision:** Design thoroughly now, implement post-MVP. Columns added to `style_bridges` table (`phi_score`, `cnn_structural_score`) but left nullable/unused.
**Rationale:**
- MVP needs working search + bridges first
- IIT implementation requires baseline metrics to measure improvement against
- 6-10 weeks is a significant investment; portfolio launch shouldn't wait for it
- Design now means the architecture accommodates it cleanly
**Alternatives considered:** Implement basic Φ in MVP (scope creep risk); skip IIT entirely (lose competitive differentiation)
**Outcome:** 78K-word design doc ([docs/IIT_4.0_INTEGRATION_PLAN.md](IIT_4.0_INTEGRATION_PLAN.md)), quick reference ([docs/IIT_REFERENCE.md](IIT_REFERENCE.md)), CNN integration plan ([docs/CNN_INTEGRATION_SUMMARY.md](CNN_INTEGRATION_SUMMARY.md)); zero implementation code; DB columns reserved

---

### 10. Product Strategy: Intelligence Layer as the Moat

**Date:** ~2026-02-18
**Context:** What makes Vintage Vestige defensible as a product?
**Decision:** The moat is the knowledge graph (enriched metadata + style bridges), not the search UI or the data itself.
**Rationale:**
- Museums and datasets are publicly available — anyone can collect the data
- The enrichment pipeline (Claude + Fashionpedia taxonomy) produces structured intelligence that doesn't exist elsewhere
- Style bridges reveal non-obvious cross-era connections
- This intelligence can be packaged as an API (Style DNA API) for B2B
**Alternatives considered:** Focus on consumer search (commoditized); focus on data volume (expensive, no moat); focus on scraping infrastructure (legally risky)
**Outcome:** 3-layer architecture centered on intelligence; 6 customer segments identified; 5-phase roadmap from MVP to platform
**Reference:** [docs/reference/fashion_intelligence_platform.md](reference/fashion_intelligence_platform.md)

---

### 11. Schema-First API Design: Define Contracts Before Endpoints

**Date:** 2026-02-21
**Context:** Starting FastAPI implementation. Could write routers first or schemas first.
**Decision:** Define all 13 Pydantic schemas first (Day 1), then write routers (Day 2).
**Rationale:**
- Schemas are the contract between three layers (TypedDict query results, ORM models, frontend TS types)
- Cross-referencing all three sources of truth upfront caught alignment issues (dead columns, mismatched filter fields)
- Once schemas were verified against live data, routers became trivial (`model_validate()` handles everything)
- Caught 5 dead columns before they became API baggage
**Alternatives considered:** Write routers first with inline dicts (faster to start, harder to maintain)
**Outcome:** 13 schemas verified against live DB; routers averaged ~5 lines per endpoint

---

### 12. Native SQL Filtering Over Python Post-Filtering

**Date:** 2026-02-22 (updated 2026-03-05 for pgvector migration)
**Context:** Text search needs optional filters (era, decade, garment_type, etc.). Two approaches: (A) fetch extra results and filter in Python, (B) pass filters natively to the database.
**Decision:** Option B — build SQL WHERE clauses from `SearchFilters` schema and include in the pgvector query.
**Rationale:**
- Database prunes the search space before vector comparison — faster and more accurate
- `model_dump(exclude_none=True)` makes the filter builder generic (works for any subset of filter fields)
- Filters are native SQL WHERE clauses alongside pgvector `<=>` cosine distance
**Alternatives considered:** Post-filtering in Python (simpler but returns fewer relevant results for a given limit)
**Outcome:** Clean helper function `_build_filter_dict()` that converts any SearchFilters → SQL WHERE params
**Note:** Originally implemented with Qdrant filters; migrated to SQL WHERE clauses on 2026-03-04

---

### 13. ~~Backfill vintage_images Payloads~~ (OBSOLETE)

**Date:** 2026-02-22
**Superseded by:** Decision #27 (Qdrant → pgvector migration, 2026-03-04)
**Note:** This decision was about syncing Qdrant payload fields. With pgvector, embeddings are columns on the products table — no separate payload to keep in sync. The problem this solved no longer exists.

---

### 14. No API Version Prefix (/api/v1)

**Date:** 2026-02-22
**Context:** Old `main.py` stub had `prefix="/api/v1"` on router includes. Frontend API client calls `http://localhost:8000/search/text` directly.
**Decision:** No prefix. Routes are `/search/text`, `/products/{id}`, `/bridges/top`, etc.
**Rationale:**
- Frontend already written to call endpoints without prefix
- For an MVP/portfolio project, versioning adds complexity without benefit
- Can add a prefix later if needed (single change in main.py)
**Alternatives considered:** Keep `/api/v1` prefix (would require changing frontend API client)
**Outcome:** Routes match frontend expectations exactly

---

### 15. Mobile-First Frontend Design (390px Base)

**Date:** 2026-02-23
**Context:** Planning the frontend implementation. Need to decide whether to design desktop-first or mobile-first.
**Decision:** Mobile-first design starting at 390px viewport width, enhanced for tablet (768px) and desktop (1440px).
**Rationale:**
- Primary audience is Gen Z / younger Millennials (18-35) discovering vintage fashion — phone-first behavior
- Consumer-facing fashion discovery tools get most traffic on mobile
- Mobile constraints force better prioritization of content and interactions
- Progressive enhancement is cleaner than graceful degradation
**Alternatives considered:** Desktop-first with responsive shrinkdown (standard for dashboards, but wrong for consumer tools)
**Outcome:** All components in the implementation plan specify mobile layout first, then desktop enhancements. Key adaptations: BridgeCardFull images stack vertically on mobile vs. side-by-side on desktop; product grid is 2-col on mobile vs. 4-col on desktop; header uses hamburger menu on mobile vs. inline nav on desktop.
**Reference:** [docs/plans/FRONTEND_IMPLEMENTATION_PLAN.md](plans/FRONTEND_IMPLEMENTATION_PLAN.md)

---

### 16. Typography: Cormorant Garamond Over Playfair Display

**Date:** 2026-02-23
**Context:** Figma design handoff specified Cormorant Garamond. The existing scaffold uses Playfair Display.
**Decision:** Switch serif font from Playfair Display to Cormorant Garamond (weights: 400, 500, 600, 700 + italic 400).
**Rationale:**
- Cormorant Garamond is more editorial and vintage-appropriate — lighter, more elegant proportions
- Better readability at body text sizes (Playfair is heavier, better suited for large headlines only)
- Available on Google Fonts, so no change to the loading pattern
**Alternatives considered:** Keep Playfair Display (already in the scaffold); EB Garamond (closer to true Garamond but less refined at display sizes)
**Outcome:** Phase 1.1 of the implementation plan covers the font swap in layout.tsx

---

### 17. New Color Token System (Replacing vintage.* Namespace)

**Date:** 2026-02-23
**Context:** The existing Tailwind config uses a `vintage.*` color namespace. The Figma design handoff defines a more specific palette with semantic groupings (core, borders, accents, platforms, scores).
**Decision:** Replace `vintage.*` with new semantic tokens: core (cream, charcoal, muted), borders (border, border-light), accents (terracotta, gold, sage), platforms (met, smithsonian, fashionpedia, etsy, depop), scores (semantic, visual, structural).
**Rationale:**
- Semantic naming (e.g., `terracotta` vs `burgundy`) better matches the design system intent
- Platform-specific colors enable visual differentiation of data sources
- Score-type colors enable meaningful bridge score breakdown visualization
- Grouping by purpose (core/border/accent/platform/score) is more scalable than a flat namespace
**Alternatives considered:** Keep `vintage.*` and add new tokens alongside (naming collisions, confusion)
**Outcome:** Phase 1.2 of the implementation plan covers the full palette replacement

---

### 18. Aligned SearchFilters and FilterOptions (8 Matching Dimensions)

**Date:** 2026-02-21
*(Originally decision #15, renumbered after 2026-02-23 additions)*
**Context:** `SearchFilters` (what users send with search) and `FilterOptions` (what `/filters` returns) had different fields.
**Decision:** Align both to exactly 8 fields: era, decade, garment_type, vibe, occasion, fit_style, culture, material.
**Rationale:**
- 1:1 mapping means every dropdown option is a valid search filter
- Dropped `season` (0/866 populated in practice)
- Dropped `platform` and `fp_category` from user-facing filters (internal fields)
**Alternatives considered:** Keep them separate with different field sets (confusing UX — filters that don't work)
**Outcome:** Frontend can populate filter dropdowns directly from `/filters` response, every value is guaranteed to produce results

---

### 19. ProductCard Union Type (SearchResult | ProductSummary)

**Date:** 2026-02-25
**Context:** ProductCard needs to display items from both search results and bridge endpoints. These return different types (`SearchResult` has `score`, `ProductSummary` doesn't).
**Decision:** Accept a union type `CardData = SearchResult | ProductSummary` with a `hasScore()` type guard to distinguish them.
**Rationale:**
- One card component for both contexts avoids code duplication
- Type guard provides TypeScript-safe access to `score` only when available
- Optional `score` prop allows passing score externally (from bridge data)
**Alternatives considered:** Two separate card components (redundant); single type with optional fields (loses type safety)
**Outcome:** Single `ProductCard` reusable across search results, bridge displays, and product listings

---

### 20. Runtime Inline Styles for Dynamic Colors

**Date:** 2026-02-25
**Context:** PlatformBadge, ScoreCircle, and ScoreBreakdown need colors that come from JS objects at runtime (e.g., `PLATFORM_COLORS[platform]`). Tailwind classes must be known at build time.
**Decision:** Use inline `style={{ color: platformColor }}` for runtime-computed colors instead of Tailwind classes.
**Rationale:**
- Tailwind's JIT compiler can't generate classes from dynamic values (`text-[${color}]` doesn't work)
- The color values are already defined in `theme.ts` as JS constants
- Inline styles for color only — layout/spacing still uses Tailwind
**Alternatives considered:** Tailwind safelist (bloats CSS with all possible values); CSS custom properties (extra indirection for no benefit)
**Outcome:** Clean pattern: Tailwind for layout, inline style for runtime colors

---

### 21. Frontend Page Route `/product/[id]` (Singular)

**Date:** 2026-02-25
**Context:** API uses `/products/{id}` (REST plural convention). Frontend page route could be `/product/` or `/products/`.
**Decision:** Use singular `/product/[id]` for the frontend page route.
**Rationale:**
- URL slugs conventionally use singular for viewing one resource (`/product/123`, not `/products/123`)
- API convention (plural) and URL convention (singular) serve different purposes
- Matches user mental model: "I'm looking at a product"
**Alternatives considered:** `/products/[id]` to match API (would work but feels like a list endpoint)
**Outcome:** `app/product/[id]/page.tsx` will be the product detail page

---

### 22. Belt-and-Suspenders Image Fallback Strategy

**Date:** 2026-02-27
**Context:** BridgeCardFull, BridgeCardCompact, and ProductCard all display images using `next/Image`. We added an `ImageWithFallback` component that catches load errors and shows a gradient. Should we remove the existing ternary fallbacks (`product.primary_image ? <Image> : <gradient div>`) now that ImageWithFallback handles errors?
**Decision:** Keep both — ternary fallback for missing URLs, ImageWithFallback for broken URLs.
**Rationale:**
- Ternary catches the `null`/empty URL case before any network request
- ImageWithFallback catches the runtime case where a URL exists but fails to load (404, CORS, etc.)
- Both failure modes exist in the dataset (museum CDN URLs change, some items lack images)
- Marginal extra code, no performance cost
**Alternatives considered:** Remove ternaries and let ImageWithFallback handle everything (would still try to load `src=""` or `src={null}` which is invalid)
**Outcome:** All image-displaying components use both layers

---

### 23. ISR Caching for Home Page (1-Hour Revalidation)

**Date:** 2026-02-27
**Context:** Home page calls `getTopBridges()` on every request. Bridges don't change often — they're only recomputed during data growth phases.
**Decision:** `export const revalidate = 3600` — Next.js ISR caches the page for 1 hour.
**Rationale:**
- Bridge data is essentially static between data growth sessions
- Reduces database load for the most-visited page
- 1 hour is conservative enough to pick up changes without manual cache purging
- No user-specific content on home page — safe to cache globally
**Alternatives considered:** `revalidate = 0` (SSR every request — unnecessary load), `revalidate = 86400` (24 hours — too stale during active development)
**Outcome:** Home page served from cache, revalidated hourly

---

### 24. Grow Dataset Before Deploying

**Date:** 2026-02-27
**Context:** Frontend is complete and builds clean. Could deploy now with 866 products, or grow to 1,500 first.
**Decision:** Grow to 1,500 products before first deployment.
**Rationale:**
- Sparse data means many search queries return few results — bad first impression
- Product detail pages show style ancestry and siblings sections that look empty with few bridges
- Bridge diversity improves with more products (more cross-platform, cross-era connections)
- Deployment config doesn't change whether you have 866 or 1,500 products
- Growth plan is documented and ready to execute (~$27 Claude API cost)
**Alternatives considered:** Deploy now, grow later (would work technically but poor UX for portfolio piece)
**Outcome:** Database growth plan at `.claude/plans/functional-hopping-barto.md`, deployment deferred

---

### 25. Fashionpedia-Heavy Growth Distribution

**Date:** 2026-02-27
**Context:** Growing from 866 → 1,500 products. Need to decide distribution across 3 sources (Fashionpedia, Met Museum, Smithsonian).
**Decision:** Target Fashionpedia 750 (+250), Met 400 (+200), Smithsonian 350 (+184).
**Rationale:**
- Fashionpedia items come with 11 expert-annotated taxonomy fields from the source dataset
- This means Fashionpedia items only need "creative_only" enrichment ($0.015/item) vs full enrichment ($0.03/item) for museum items
- More Fashionpedia = lower Claude API cost for same product count
- Met and Smithsonian still grow meaningfully for cross-platform bridge diversity
**Alternatives considered:** Even distribution (more expensive — more full-enrichment items); museum-heavy (richer metadata but 2x Claude cost)
**Outcome:** Estimated total enrichment cost: $15.27 (vs ~$19 for even split)

---

### 26. Deployment Architecture: Specialized Platforms Per Service

**Date:** 2026-02-27
**Context:** Need to deploy 4 services: FastAPI, Next.js, PostgreSQL, Qdrant. Could use one platform for everything or specialize.
**Decision:** Recommended approach: Supabase (Postgres + pgvector + Storage) + Railway (FastAPI) + Vercel (Next.js).
**Rationale:**
- Each platform is best-in-class for its service type
- Most generous free tier per service (important for portfolio project)
- Vercel is purpose-built for Next.js (zero-config deployment)
- Supabase handles Postgres + pgvector + image storage in one service
**Alternatives considered:** Railway for everything (simpler but less generous free tier), Fly.io (good but more CLI-driven), self-hosted (too much ops burden), Qdrant Cloud (eliminated by Decision #27)
**Outcome:** Decision documented, not yet executed (waiting for data growth)
**Updated:** 2026-03-05 — Qdrant Cloud removed per Decision #27

### 27. Switch from Qdrant to Supabase pgvector for Vector Storage

**Date:** 2026-03-04
**Context:** Had local Qdrant (2 collections: vintage_text 384d, vintage_images 512d) + local PostgreSQL. Migrating to Supabase for managed hosting. Needed to decide whether to use Qdrant Cloud or consolidate into pgvector.
**Decision:** Eliminate Qdrant entirely. Store embeddings as pgvector columns (`text_embedding vector(384)`, `image_embedding vector(512)`) directly on the `products` table in Supabase PostgreSQL.
**Rationale:**
- Single database for everything — no separate vector DB to manage, pay for, or keep in sync
- Both embeddings on the same row makes IIT cross-modal Φ calculation simpler (single SQL query vs cross-collection Qdrant lookups)
- pgvector HNSW indexes provide comparable performance at our scale (866 embedded products)
- Supabase already running for the project — zero additional infrastructure
- `VectorSearch` class shares the SQLAlchemy session — no separate connection pool
**Alternatives considered:** Qdrant Cloud free tier (1GB, would work but adds operational complexity); keep local Qdrant (not deployable)
**Outcome:** Migration complete (866 text + 866 image embeddings in pgvector). Local Qdrant stopped. `storage/vector_search.py` replaces `storage/vector_db.py`. API search layer updated.
**Revises:** Decision #26 (Qdrant Cloud is no longer part of the deployment architecture)

---

### 30. Late Fusion Over Multimodal Embedding Fusion

**Date:** 2026-03-06
**Context:** Text embeddings (MiniLM 384d from enriched_text) and image embeddings (CLIP 512d from product images) are separate vectors. Could combine into a single fused vector per product.
**Decision:** Keep separate vectors, combine scores at bridge computation time (late fusion). No single fused embedding.
**Rationale:**
- MiniLM text encoder captures semantic richness (enriched_text has 23 fields including vibes, era, materials)
- CLIP captures visual similarity (shape, color, texture)
- These are genuinely different signals — "looks similar" ≠ "means similar"
- Late fusion preserves the ability to weight modalities differently (bridge formula: 0.40 text + 0.30 image + 0.30 structural)
- A fused vector would lose the MiniLM semantic advantage (CLIP text encoder doesn't understand fashion vocabulary as well)
**Alternatives considered:** Early fusion (average CLIP text + image vectors — loses MiniLM richness); concatenation (896d, mathematically dubious); learned projection (requires training data we don't have)
**Outcome:** Current architecture is stronger for fashion cross-era matching than any single-vector approach

---

### 31. Async Concurrent Enrichment Over Sequential or Batch API

**Date:** 2026-03-06
**Context:** ~3,298 products needed enrichment. Sequential processing via `enrich_remaining.py` estimated ~5.5 hours. Two alternatives: Claude Message Batches API (50% cost, 24hr turnaround) or async concurrent requests.
**Decision:** Built `enrich_async.py` with `asyncio.Semaphore`-bounded concurrency (default 5 concurrent requests).
**Rationale:**
- ~5x speedup over sequential (semaphore limits to N concurrent API calls)
- Real-time progress feedback (rate, ETA, error count every 10 completions)
- User familiar with asyncio from prior experience
- Batch API saves 50% cost but has up to 24hr turnaround — user preferred speed and feedback
**Alternatives considered:** Message Batches API (`enrich_batch.py` also built as option); sequential `enrich_remaining.py` (too slow)
**Outcome:** User running batches of 300 at concurrency 5; 624 products enriched in first session

---

### 32. Embedding Generation Separate from Enrichment

**Date:** 2026-03-06
**Context:** `enrich_async.py` originally included embedding generation in phase 2 (after API calls). User pointed out they'd always done embedding as a separate step.
**Decision:** Keep enrichment and embedding as separate pipeline stages. `enrich_async.py` only does Claude API calls + DB writes. Embeddings generated via `generate_all_embeddings.py` and `generate_image_embeddings.py`.
**Rationale:**
- User's established workflow — muscle memory matters
- Cleaner separation of concerns (API-bound vs CPU-bound)
- Can re-embed without re-enriching (useful when embedding model changes)
- Embedding scripts already exist and work well
**Alternatives considered:** All-in-one enrichment + embedding (simpler but less flexible)
**Outcome:** Pipeline remains: enrich → embed text → embed images → compute bridges

---

### 33. Use enriched_text for Text Embeddings (Not Raw Title+Description)

**Date:** 2026-03-06
**Context:** `generate_embeddings_for_database()` was embedding `title + description` (raw product metadata). But `enriched_text` contains 23 Claude-enriched fields (vibes, era, materials, style tags, etc.) — much richer semantic content.
**Decision:** Changed text embedding source to `enriched_text` with fallback to `title + description`. Also changed filter from `embedded_at == None` to `enriched_at != None, text_embedding == None`.
**Rationale:**
- enriched_text is the whole point of the enrichment pipeline — embedding raw titles throws away the intelligence layer
- MiniLM embeddings of enriched_text capture vibes, style tags, era context that raw titles lack
- Filter change ensures we only embed products that have been enriched (prevents embedding raw data)
**Alternatives considered:** Keep embedding raw titles (baseline, but defeats the purpose of enrichment)
**Outcome:** New embeddings use enriched_text; old 866 products need re-embedding
**Revises:** Previous behavior where embeddings used `title + description`

---

### 28. Supabase Storage for Product Images (Replace Base64)

**Date:** 2026-03-04
**Context:** 4,234 products had images stored as base64 `data:image/jpeg;base64,...` strings in the `primary_image` column. This bloated the database (~163 MB of image data in PostgreSQL).
**Decision:** Migrate all images to Supabase Storage (public bucket `product-images`), replace `primary_image` with HTTP URLs.
**Rationale:**
- Database shrinks from ~179 MB to ~19 MB (base64 removed)
- CDN-served images load faster than base64-decoded blobs
- Supabase Storage is free up to 1 GB (our images are well under)
- HTTP URLs work directly with `next/image` and any frontend
**Alternatives considered:** Keep base64 (simple but bloated); external CDN like Cloudflare R2 (more config for no benefit at our scale)
**Outcome:** All 4,234 products migrated. Zero base64 remaining. Images accessible at `https://tusswxlrdoamintvswjs.supabase.co/storage/v1/object/public/product-images/{id}.jpg`

---

### 29. VectorSearch Shares SQLAlchemy Session (Not Own Connection)

**Date:** 2026-03-04
**Context:** Old `VectorDB` class managed its own Qdrant connection. New `VectorSearch` needs to decide: own connection or share the request's DB session?
**Decision:** `VectorSearch.__init__(self, db: Session)` — takes the request's SQLAlchemy session via FastAPI `Depends()`.
**Rationale:**
- Vector search and relational queries are in the same database now (pgvector)
- Sharing the session means they participate in the same transaction
- FastAPI's dependency injection handles session lifecycle (open/close per request)
- Simpler than managing a separate connection pool
**Alternatives considered:** Own engine/session (would work but wasteful — two connections to the same DB per request)
**Outcome:** Clean dependency chain: `get_db()` → `get_vector_search(db)` → router

---

### 34. 6-Dimensional Bridge Classification Over Single semantic_type

**Date:** 2026-03-07
**Context:** The `semantic_type` column was a single overloaded string (7 values) that conflated temporal distance, categorical crossing, and aesthetic connection. Impossible to filter "all contrast bridges that are cross-cultural transmissions."
**Decision:** Replace with 6 orthogonal columns: `temporal_type`, `crossing_type`, `connection_mode`, `primary_axis`, `secondary_axis`, `contrast_pair`.
**Rationale:**
- Each dimension answers a different question about the bridge
- Enables precise filtering in API and frontend (any combination of dimensions)
- Provides structured input for narrative generation (mode-specific prompts)
- Supports future KG schema (each dimension becomes a node property)
**Alternatives considered:** Adding flags alongside semantic_type (still conflated); machine learning classifier (not enough labeled data)
**Outcome:** 6 columns added to StyleBridge, classifier script built, tests passing. Pending: classifier run after bridge recomputation.
**Reference:** `scripts/classify_bridge_dimensions.py`, `.claude/plans/zazzy-seeking-falcon.md`

---

### 35. 3 Connection Modes (contrast/resonance/affinity) Over 5

**Date:** 2026-03-07
**Context:** Initially designed 5 connection modes: citation, echo, parallel, contrast, kinship. On critique:
- **echo** was "not kinship" rather than identifying something specific (any shared material triggered it)
- **parallel** was too rare (triple condition: structural > 0.5 + text < 0.6 + image < 0.5)
- **citation** implied intentional reference that can't be detected from embeddings alone
**Decision:** Simplify to 3 sharp modes: **contrast** (opposing vibes on structural axis), **resonance** (same aesthetic language across time), **affinity** (everything else — axis tells the story).
**Rationale:**
- Each mode now identifies something genuinely distinct and actionable
- Contrast is the most interesting (shown in rose), resonance shows temporal echoes (amber), affinity is the baseline (gray)
- Fewer modes = cleaner UX, clearer mental model
**Alternatives considered:** Keep 5 modes with secondary_mode flag; 4 modes (keep echo)
**Outcome:** Classifier implements 3 modes with priority: contrast > resonance > affinity

---

### 36. Post-Hoc Bridge Classification (Not Integrated into compute_bridges)

**Date:** 2026-03-07
**Context:** Could integrate classification into `compute_bridges.py` (classify during discovery) or run as a separate post-processing step.
**Decision:** Separate `scripts/classify_bridge_dimensions.py` runs after bridge computation.
**Rationale:**
- `compute_bridges.py` is already complex (2-pass pgvector search + scoring)
- Classification depends on fields that bridge computation doesn't need (core_vibes, bridge_vibes)
- Can re-classify without recomputing bridges (e.g., when tuning thresholds)
- Can dry-run to review distribution before committing
**Alternatives considered:** Inline classification during bridge creation (tighter coupling, can't re-classify independently)
**Outcome:** Clean separation — compute bridges, then classify, then generate narratives

---

### 37. Social Function Explorer as Separate /explore Router

**Date:** 2026-03-07
**Context:** Needed endpoints for browsing products by social function. Could extend `/products` or create new router.
**Decision:** New `/explore` router with function-specific endpoints.
**Rationale:**
- Conceptually different from single-product CRUD (discovery vs. detail)
- Will grow with technique explorer, motif explorer, etc.
- Clean URL structure: `/explore/functions`, `/explore/techniques` (future)
- Uses `jsonb` containment operators for efficient JSON array querying
**Alternatives considered:** Add to products router (would clutter it); generic faceted search (over-engineered for now)
**Outcome:** 2 endpoints (`/explore/functions`, `/explore/functions/{fn}`) + `shared_function` filter on bridges/top

---

### 38. Scripts in `tools/`, Library Code in Package Dirs

**Date:** 2026-03-09
**Context:** Project reorganization for deployment. Scripts were scattered across 5 locations (enrichment/scripts/, embeddings/, scripts/, storage/load_data/, etc.). The Dockerfile needed to know exactly what the API container needs.
**Decision:** Move all runnable scripts to `tools/` subdirectories (analysis, enrichment, embeddings, data_loading, data_quality, db_utils, migration). Keep only library code (imported at runtime by the API) in package dirs (api/, storage/, embeddings/, enrichment/, analysis/).
**Rationale:**
- Dockerfile says "COPY these 5 dirs" and gets exactly what the API needs — no scripts, no loaders
- `.dockerignore` is one line: `tools/`
- Clean separation: library code is imported, scripts are executed
- All scripts use same `sys.path.insert(0, project_root)` pattern with `'..', '..'` for 2-level nesting
**Alternatives considered:** Dockerignore individual directories (fragile, doesn't scale); copy everything (bloated container)
**Outcome:** 16+ scripts moved, all tests passing (158 unit, 70 integration)

---

### 39. Decade-Based Temporal Fallback Before Platform Proxy

**Date:** 2026-03-09
**Context:** `classify_temporal_type` fell back to platform proxy (historical vs. modern) when no era data existed. But the V&A museum spans many centuries — same platform doesn't mean same era.
**Decision:** Insert decade-based fallback between era-based classification and platform proxy. Parse decades to midpoint years, compute gap, classify by distance. Only use platform proxy when one side is historical and the other modern. Return `None` when truly no temporal data exists for same-platform pairs.
**Rationale:**
- Decades are more reliable than platform as a temporal signal
- V&A has items from 1600s to 2000s — `va_museum` vs `va_museum` tells you nothing about time
- `None` is better than a wrong answer — downstream code can handle unknown
**Alternatives considered:** Remove platform fallback entirely (loses useful signal for met_museum vs fashionpedia); keep platform fallback as-is (wrong for V&A)
**Outcome:** Fixed in `compute_bridges.py`, consolidated as single source of truth (deleted duplicate from `classify_bridge_dimensions.py`)

---

### 40. Single Source of Truth for `classify_temporal_type`

**Date:** 2026-03-09
**Context:** `classify_temporal_type` was defined in both `compute_bridges.py` and `classify_bridge_dimensions.py` with diverging implementations.
**Decision:** Delete from `classify_bridge_dimensions.py`, import from `compute_bridges.py`.
**Rationale:**
- One function, one definition — DRY principle
- `compute_bridges.py` is the canonical location (it uses the function during bridge creation)
- `classify_bridge_dimensions.py` can import it alongside `CATEGORY_GROUPS` and other shared constants
**Outcome:** Single definition, both scripts share it

---

### 41. Mode-Specific Composite Scoring in SQL

**Date:** 2026-03-09
**Context:** Bridge composite scores in SQL used `COALESCE(image_similarity, 0)` which penalized bridges without images. Python code redistributed weights proportionally. SQL and Python ordering disagreed.
**Decision:** Rewrite SQL composite score as a 6-branch CASE statement matching Python's exact weight redistribution for each connection mode (contrast/resonance/affinity) × (with/without image).
**Rationale:**
- SQL ordering must match Python scoring — they're the same concept
- COALESCE(image_similarity, 0) effectively punishes bridges without images by counting 0 for 30% of the score
- Proportional redistribution (divide by sum of available weights) is fairer and matches `_build_bridge_result()` in Python
**Alternatives considered:** Add image_similarity to all bridges (not feasible — some products lack images); always COALESCE to 0 in both SQL and Python (unfair to text-only bridges)
**Outcome:** `_COMPOSITE_SQL` uses `literal_column()` with 6-branch CASE; `_COMPOSITE_DESC` uses `text()` for ORDER BY

---

### 42. Narrative Length Differentiated by Connection Mode

**Date:** 2026-03-09
**Context:** All bridge narratives used the same length constraint regardless of mode. Contrast bridges need to explain both shared ground and divergence — more complex than "these two things are similar."
**Decision:** Contrast bridges: 2 sentences, max 60 words. Resonance and affinity: 1 sentence, max 40 words.
**Rationale:**
- Contrast narratives have two parts: "what they share" (sentence 1) and "how they diverge" (sentence 2)
- Resonance/affinity can be captured in one sentence — they're describing a single relationship, not a tension
- Word limits prevent verbose AI output while giving contrast enough room
**Alternatives considered:** Same length for all (contrasts feel cramped); no word limit (narratives balloon)
**Outcome:** Mode-specific system prompts in `enrichment/claude.py`

---

### 43. Opposition Composite Sort Score (Pass 2)

**Date:** 2026-03-13
**Context:** Pass 2 (opposition bridges) was sorted by raw `structural_score`, which rewarded generic high-overlap pairs (blazer vs blazer) over genuinely interesting cross-era, cross-cultural contrasts.
**Decision:** Sort opposition bridges by composite: `0.40 * cc_norm + 0.35 * temporal_norm + 0.25 * structural_score`, where `cc_norm` is normalized Jaccard over the 3 cross-cultural fields (construction_technique, social_function, motif_family) and `temporal_norm` is era midpoint gap / 200 years.
**Rationale:**
- Cross-cultural field overlap signals that items with opposing vibes share a deeper structural conversation
- Temporal distance makes the opposition more historically interesting
- Raw structural score still contributes but doesn't dominate
**Alternatives considered:** Keep structural_score sort (rewards generic garments); weight equally (temporal distance gets too much weight when era data is sparse)
**Outcome:** Implemented in `tools/analysis/compute_bridges.py` Pass 2. `_sort_score` key stripped before INSERT to avoid CompileError.

---

### 44. Near-Duplicate Detection Across All Passes

**Date:** 2026-03-13
**Context:** Bridge computation could produce near-identical pairs — different records for the same garment from different museum catalogues, or digitized + original pairs.
**Decision:** Two-layer duplicate filter in every pass: (1) exact title match → always skip; (2) same era + text_sim ≥ 0.95 → skip. Extended to catch cross-platform duplicates (dropped the single-platform restriction from Pass 1).
**Rationale:**
- Same title is an obvious duplicate signal regardless of platform
- text_sim ≥ 0.95 with same era means descriptions are nearly identical — the bridge adds no insight
- Cross-platform duplicates (same garment photographed by two museums) are real and should be filtered
**Alternatives considered:** Only filter exact title matches (misses near-duplicates with slightly different titles); filter all same-era high-similarity pairs regardless of threshold (too aggressive, removes valid bridges between similar but distinct garments)
**Outcome:** Implemented in all 4 passes in `tools/analysis/compute_bridges.py`.

---

### 45. Same-Era Vibe Gate on Passes 3 and 4

**Date:** 2026-03-13
**Context:** Pass 3 (shared purpose) and Pass 4 (structural) were finding same-era pairs that shared a function or structure but had identical aesthetics — low insight "look at these two similar things from the same time."
**Decision:** After boundary checks (cross-platform or cross-category), require `_vibes_diverge()` for same-era pairs. Two items from the same era only form a bridge if their core_vibes or bridge_vibes include at least one opposition pair or no overlapping vibes.
**Rationale:**
- Same-era + same-function + same-vibes = uninformative bridge
- Divergent vibes mean the two items are asking different aesthetic questions with the same functional vocabulary — that's interesting
**Alternatives considered:** No vibe gate (allows same-era duplicates through); require vibe gate on all pairs regardless of era (too aggressive, removes valid same-era cross-category bridges)
**Outcome:** `_vibes_diverge()` helper added to `compute_bridges.py`; gate applied in passes 3 and 4.

---

### 46. Social Function Consolidation (101 → ~20 Canonical Clusters)

**Date:** 2026-03-13
**Context:** `social_function` had 101 distinct freeform values from Claude enrichment — too fragmented for meaningful grouping in Pass 3 (shared purpose discovery).
**Decision:** Map 101 values to ~20 canonical clusters via `tools/analysis/consolidate_social_function.py`. Support multi-cluster mapping (e.g. garments serving both `wedding-ceremonial` and `status-display` purposes). Updated compute_bridges to treat `social_function` as an array and use set intersection for grouping.
**Rationale:**
- 101 values means most social_function groups in Pass 3 have 1-2 members — no meaningful cross-era discovery
- ~20 clusters create groups large enough (20-150 products) to find cross-cultural bridges
- Multi-cluster support handles genuinely mixed-purpose garments correctly
**Alternatives considered:** Enumerate clusters manually without script (fragile, not reproducible); normalize to single value per garment (loses nuance for mixed-purpose items)
**Outcome:** Applied to database. `compute_bridges.py` Pass 3 uses array containment for group matching.

