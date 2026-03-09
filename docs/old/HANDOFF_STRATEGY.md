# Vintage Vestige — Strategy & Business Handoff

*For discussion with Claude Desktop on strategy, branding, marketing, profit potential, and work quality assessment.*

---

## What Is Vintage Vestige?

Vintage Vestige is a **fashion knowledge graph** that discovers hidden connections between historical garments and modern fashion. It bridges museum archives (The Met, Smithsonian) with contemporary fashion databases (Fashionpedia) — and eventually marketplace listings (Etsy, Depop) — revealing how design DNA travels across time, culture, and category.

The core product is the **Style Bridge**: a computed relationship between two fashion items showing what they share structurally, visually, and semantically — even when they're centuries apart.

**Example bridge:** A Victorian bustle dress from The Met (1870s) connected to a modern peplum blouse on Etsy (2020s) — both share the same waistline emphasis, flared silhouette below the waist, and structured construction. The bridge explains *why* they're connected and scores the strength of the relationship.

---

## What's Been Built

### Data Pipeline (Python)
- **866 products** ingested from 3 sources:
  - The Metropolitan Museum of Art (200 items, via API)
  - Smithsonian Institution (166 items, via API)
  - Fashionpedia (500 items, academic fashion taxonomy dataset)
- **AI enrichment** via Claude Sonnet 4: every product has 23+ metadata fields including era, decade, culture, vibe, silhouette, materials, AI-written descriptions, and full Fashionpedia structural taxonomy
- **Dual embedding system**: text embeddings (all-MiniLM-L6-v2, 384d) + image embeddings (CLIP ViT-B-32, 512d) stored in Qdrant vector database

### Bridge Computation Engine
- **7,324 style bridges** computed across all products
- **4-pass discovery system** per product:
  1. Open discovery — strongest connections regardless of source
  2. Cross-category — similar construction DNA, different garment type (e.g., dress construction in a jacket)
  3. Cross-vibe — similar structure, different aesthetic (e.g., dark academia meets bohemian)
  4. Cross-culture — similar structure, different cultural origin
- **6 bridge types**: cross_era, cross_time, revival, cross_category, cross_vibe, cross_culture
- **Composite scoring formula**: 40% text similarity + 30% image similarity + 30% structural overlap
- **Structural scoring**: 12 Fashionpedia taxonomy fields with weighted comparison (exact match for scalars, Jaccard similarity for sets like garment parts and decorations)
- **AI narratives**: Every bridge has a Claude-generated 1-2 sentence explanation of the connection

### REST API (FastAPI)
- Full CRUD for products and bridges
- Filtered search (by platform, era, type, score range)
- Bridge statistics and histogram endpoints
- Pagination throughout

### Frontend (Next.js + TypeScript + Tailwind)
- Design system with warm vintage-meets-modern aesthetic
- Component library: bridge cards (compact + full), score circles, score breakdowns, attribute pills, narrative blocks, platform/era badges
- Figma design handoff document exists for UI reference

### Test Suite
- **105 unit tests** (no DB required)
- Integration tests against live PostgreSQL + Qdrant
- Data integrity tests (deduplication invariants, score ranges, type validation)
- HTML bridge visualization report generator

---

## What Makes This Novel

1. **Cross-temporal fashion graph**: No existing product connects museum archives to modern fashion through computed structural similarity. Fashion history sites are editorial; marketplace sites are transactional. This is analytical.

2. **Structural taxonomy as bridge DNA**: Using Fashionpedia's 46-category garment taxonomy to compute *why* things are connected, not just *that* they are. The shared attributes (same neckline, same silhouette, same construction technique) make bridges explainable.

3. **Named-era classification**: Instead of rigid year-distance thresholds, bridges use named aesthetic eras (Victorian, Art Deco, Quiet Luxury) that capture conceptual distance. A "revival" bridge type specifically identifies modern pieces that reproduce historical construction patterns.

4. **Multi-signal scoring**: Combining semantic similarity (text), visual similarity (CLIP image embeddings), and structural overlap (taxonomy) produces more meaningful connections than any single signal alone.

---

## Current Data State

| Source | Count | Culture | Era | Decade | Images |
|--------|-------|---------|-----|--------|--------|
| Fashionpedia | 500 | 0% (pending re-enrichment) | 100% | 100% | 100% |
| Met Museum | 200 | 100% | 100% | 100% | 100% |
| Smithsonian | 166 | 100% | 100% | 100% | 100% |

**Current bridge distribution** (will change after type system rebuild):
- same_era: 3,957 (54%) — *being removed*
- cross_category: 1,760 (24%)
- cross_era: 1,076 (15%)
- near_era: 425 (6%) — *being removed*
- cross_vibe: 106 (1%)

**After rebuild**, bridge types will be: cross_era, cross_time, revival, cross_category, cross_vibe, cross_culture. The same_era and near_era types are being eliminated — the app focuses on connections that transcend aesthetic periods.

---

## Immediate Roadmap

1. **Re-enrich Fashionpedia** — Fill in culture, neckline, sleeve_length fields (script ready, ~$7.50 API cost)
2. **Load marketplace data** — Etsy and Depop scrapers exist but haven't been run at scale
3. **Rebuild bridges** — Recompute all 7K+ bridges with the new type system
4. **Regenerate narratives** — New AI narratives for rebuilt bridges (~$40 API cost)
5. **Frontend pages** — Product detail, bridge explorer, search results (components built, pages not yet wired)

---

## Open Technical Questions

- **Unified vector space**: Currently text (384d) and images (512d) live in separate Qdrant collections. Could unify via CLIP's shared text-image space, a learned projection, or concatenated embeddings. Trade-offs around search flexibility vs. cross-modal matching quality.
- **Marketplace scale**: Museum data is curated (366 items). Marketplace data could be 10K+ items with much noisier metadata. How does bridge quality hold up at scale?
- **Bridge ranking**: Current scoring weights (40/30/30) were hand-tuned. Could optimize with user feedback or editorial curation.

---

## Questions for Strategy Discussion

### Branding & Positioning
- Is this a consumer product (browse fashion connections for fun), a research tool (fashion historians/students), or a marketplace feature (help sellers position vintage items)?
- "Vintage Vestige" as a name — does it communicate the right thing? It's alliterative and memorable, but does it sound too academic?
- What's the visual identity? The current UI uses warm earth tones (charcoal, gold, terracotta) with a serif-forward typography suggesting editorial quality.

### Revenue & Monetization
- **Marketplace integration**: Could Etsy/Depop sellers use bridges to price vintage items by showing their historical design pedigree?
- **API licensing**: Fashion brands or trend forecasting companies (WGSN, Edited) might want access to the cross-temporal pattern data
- **Content/editorial**: Fashion media partnerships — "The Victorian DNA in Your Wardrobe" type content
- **Consumer app**: Subscription for deep fashion exploration, or freemium with premium bridge insights?

### Quality Assessment
- The bridge computation is deterministic and explainable — every connection has a scored breakdown and shared taxonomy
- AI narratives are Claude-generated and high quality (1-2 sentences each, 100% coverage)
- The structural scoring uses an academic taxonomy (Fashionpedia), not vibes-only
- Test coverage is thorough: 105 unit tests, integration tests, data integrity invariants

### Scale & Growth
- Current: 866 products, 7,324 bridges across 3 sources
- Near-term: +marketplace data (Etsy, Depop) could 10x the product count
- The bridge computation scales O(n) per product (vector search is sublinear), so 10K products is feasible
- Each new product creates bridges to existing items — the graph gets denser and more valuable with scale

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Database | PostgreSQL (SQLAlchemy ORM) |
| Vector DB | Qdrant (text 384d, image 512d) |
| AI Enrichment | Claude Sonnet 4 (Anthropic API) |
| Text Embeddings | all-MiniLM-L6-v2 (sentence-transformers) |
| Image Embeddings | CLIP ViT-B-32 |
| API | FastAPI (Python) |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Testing | pytest (105 unit + integration + data integrity) |

---

## Key Files for Reference

- `docs/ARCHITECTURE.md` — System architecture overview
- `docs/PROJECT_STATE.md` — Detailed project state
- `docs/API_SPEC.md` — API endpoint documentation
- `analysis/compute_bridges.py` — Core bridge computation (most important file)
- `enrichment/claude.py` — AI enrichment prompts and logic
- `docs/reference/cross_source_bridges.md` — Bridge design decisions
