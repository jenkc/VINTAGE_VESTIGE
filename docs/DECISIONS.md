# Vintage Vestige — Key Decisions

**Last updated: 2026-02-23**

---

## Decision Log

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
**Decision:** `all-MiniLM-L6-v2` (384-dim) for text, `clip-ViT-B-32` (512-dim) for images. Separate Qdrant collections, not a joint embedding space.
**Rationale:**
- MiniLM is fast, small, and effective for short rich text (~256 tokens)
- CLIP handles both text and images but its text encoder is less effective for nuanced fashion descriptions than a dedicated text model
- Separate collections allow independent search and scoring
- SentenceTransformers provides both via a unified API
**Alternatives considered:** Joint CLIP space (text-image alignment but worse text quality); OpenAI embeddings (cost); BERT-large (overkill for short texts)
**Outcome:** Both models load via singleton pattern; ~500MB total download
**Trade-off:** No native cross-modal ranking — addressed by bridge scoring algorithm

---

### 4. Bridge System: 3-Pass Discovery with Canonical Ordering

**Date:** ~2026-02-19
**Context:** The core product differentiation is "style bridges" — connections between garments across eras and categories. Need to discover them at scale.
**Decision:** 3-pass Qdrant search (open discovery, cross-category, cross-vibe) → composite scoring (text + image + structural) → canonical ordering (source_id < target_id) → unique constraint.
**Rationale:**
- Open discovery finds the obvious matches; cross-category and cross-vibe find the interesting ones
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
- Python backend means embedding models and Qdrant client can run in the same process
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

### 12. Native Qdrant Filtering Over Python Post-Filtering

**Date:** 2026-02-22
**Context:** Text search needs optional filters (era, decade, garment_type, etc.). Two approaches: (A) fetch extra results from Qdrant and filter in Python, (B) pass filters to Qdrant natively.
**Decision:** Option B — build `qdrant_client.models.Filter` from `SearchFilters` schema and pass via `query_filter` parameter.
**Rationale:**
- Qdrant prunes the search space before vector comparison — faster and more accurate
- `model_dump(exclude_none=True)` makes the filter builder generic (works for any subset of filter fields)
- Only required one small change to `search_similar()` — adding a `query_filter=None` parameter
**Alternatives considered:** Post-filtering in Python (simpler but returns fewer relevant results for a given limit)
**Outcome:** Clean helper function `_build_qdrant_filter()` that converts any SearchFilters → Qdrant Filter

---

### 13. Backfill vintage_images Payloads (Not Postgres Join)

**Date:** 2026-02-22
**Context:** `vintage_images` had 12 payload fields vs 28 in `vintage_text`. Image search would be missing enrichment metadata.
**Decision:** Backfill the missing fields using Qdrant's `set_payload()` rather than joining Postgres per-request.
**Rationale:**
- One-time fix (~seconds) vs. per-request overhead (Postgres query on every image search)
- `set_payload()` merges new fields without touching vectors — CLIP embeddings are from pixel data, unaffected by metadata
- Both collections now have identical payload shapes — search router code is identical for both
- Also updated `generate_image_embeddings.py` to use full payload for future runs
**Alternatives considered:** Postgres join in image search endpoint (working but slower, more code)
**Outcome:** 866 points updated; both collections have 28 payload fields; search router has no special-casing for image vs text

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
