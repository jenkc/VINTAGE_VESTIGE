# Vintage Vestige — Technical Project Plan
**Fashion Intelligence Platform**

**Version:** 3.0 — Knowledge Graph First
**Last Updated:** February 2026
**Current Status:** Phase 1 In Progress — 1,000 items, enrichment pipeline running

---

## Strategic Framing

The product is not a search app. The product is a **fashion knowledge graph** that connects
garments across 500 years of design history. Vintage Vestige (the web app) is the consumer
demo that proves the intelligence works and generates top-of-funnel interest.

The moat is:
- Cross-source style bridges connecting historical and modern items
- Fashionpedia taxonomy harmonization across museum sources
- Enrichment pipeline tuned for fashion semantics
- Embedding spaces that understand fashion context, not generic similarity

Everything we build should deepen the graph or expose it to paying customers.

```
┌─────────────────────────────────────────────────────┐
│            PRODUCTS (what people see)                │
│                                                      │
│  Vintage Vestige    Style DNA API    Trend Oracle    │
│  (web demo/app)     (B2B SaaS)      (analytics)     │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│          INTELLIGENCE LAYER (the moat)              │
│                                                      │
│  Knowledge Graph  ·  Cross-Source Bridges            │
│  Enrichment Pipeline  ·  Taxonomy Harmonization      │
│  Embedding Spaces (visual + semantic)                │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│            DATA LAYER (raw ingredients)              │
│                                                      │
│  Met Museum  ·  Smithsonian  ·  Fashionpedia         │
│  V&A  ·  Europeana  ·  iDesigner (runway)            │
│  Etsy/Depop (eventually)  ·  User uploads            │
└─────────────────────────────────────────────────────┘
```

---

## What We Have Today

| Asset | Scale | Status |
|-------|-------|--------|
| Harmonized product database | ~1,000 items (Met, Smithsonian, Fashionpedia) | Live |
| Fashionpedia taxonomy mapping | 27 categories, 294 attributes | Complete |
| Claude enrichment pipeline | Full + creative-only paths | Running |
| Text embeddings (384-dim) | ~1,000 items in Qdrant | Live |
| Image embeddings (512-dim CLIP) | ~500 items | Partial |
| PostgreSQL schema | Products, indexes | Live |
| Web landing page | Next.js, no backend connection | Live |
| Cross-source bridge system | Designed, not built | Next up |

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    WEB CLIENTS                              │
│                                                             │
│  Vintage Vestige (Next.js)      Style DNA API consumers     │
│  • Visual search                • Resale platforms          │
│  • Era/style browsing           • Fashion brands            │
│  • Historical ↔ modern bridges  • Media / editorial         │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS / REST
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  FASTAPI BACKEND                            │
│                                                             │
│  POST /api/v1/search/image                                  │
│  POST /api/v1/search/text                                   │
│  POST /api/v1/analyze          ← Style DNA API              │
│  GET  /api/v1/products/:id                                  │
│  GET  /api/v1/bridges/:id      ← Cross-source bridges       │
│  GET  /api/v1/similar/:id                                   │
│  GET  /api/v1/timeline/:attr   ← Trend Oracle (later)       │
└──────────┬────────────────────────────┬─────────────────────┘
           │                            │
           ▼                            ▼
┌─────────────────────┐      ┌──────────────────────────────┐
│  PostgreSQL         │      │  Python AI Workers           │
│                     │      │                              │
│  products           │      │  embeddings/models.py        │
│  style_bridges      │      │  embeddings/generator.py     │
│  users (future)     │      │  enrichment/claude.py        │
│  search_history     │      │  enrichment/fashionpedia_    │
│  (future)           │      │    taxonomy.py               │
└──────────┬──────────┘      └──────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│            Qdrant Vector Database            │
│                                              │
│  vintage_images  (512-dim CLIP, cosine)      │
│  vintage_text    (384-dim MiniLM, cosine)    │
│                                              │
│  Payload fields include: platform, era,      │
│  category, product_id                        │
└──────────────────────────────────────────────┘
```

### Data Flow: Bridge-Aware Search

```
User query (text or image)
    │
    ▼ embed
Qdrant similarity search
    │
    ▼ fetch metadata
PostgreSQL products lookup
    │
    ▼ join
PostgreSQL style_bridges lookup
    │
    ▼
Response: {
  results: [...],
  each result includes:
    historical_ancestors: [...],  ← items this descended from
    modern_echoes: [...],          ← items that descended from it
    shared_attributes: {...}       ← the design DNA they share
}
```

---

## Database Schema

### `products` (existing — no changes needed)

Key fields:
- Identity: `id`, `external_id`, `platform` (met_museum | smithsonian | fashionpedia | etsy | depop)
- Content: `title`, `description`, `primary_image`, `image_urls`
- AI enrichment: `era`, `category`, `style_tags`, `silhouette`, `neckline`, `length`,
  `waistline`, `sleeve_length`, `nickname`, `textile_pattern`, `opening_type`,
  `garment_parts`, `decorations`, `textile_finishing`
- Timestamps: `created_at`, `updated_at`, `embedded_at`, `enriched_at`

### `style_bridges` (to build)

```sql
CREATE TABLE style_bridges (
    id SERIAL PRIMARY KEY,

    source_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    target_id INTEGER REFERENCES products(id) ON DELETE CASCADE,

    -- Similarity scores (0.0–1.0)
    text_similarity   FLOAT NOT NULL,
    image_similarity  FLOAT,           -- nullable: some items lack images
    structural_score  FLOAT NOT NULL,  -- % shared Fashionpedia taxonomy fields
    bridge_score      FLOAT NOT NULL,  -- weighted composite

    -- What connects them
    shared_attributes JSONB,           -- {"silhouette": "a-line", "length": "floor length"}
    bridge_type       VARCHAR(50),     -- 'historical_to_modern' | 'cross_era' | 'same_era_cross_source'
    bridge_narrative  TEXT,            -- Claude-generated one-sentence connection

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (source_id, target_id)
);

CREATE INDEX idx_bridges_source  ON style_bridges(source_id);
CREATE INDEX idx_bridges_target  ON style_bridges(target_id);
CREATE INDEX idx_bridges_score   ON style_bridges(bridge_score DESC);
CREATE INDEX idx_bridges_type    ON style_bridges(bridge_type);
```

---

## Qdrant Collections

**vintage_images** — 512-dim CLIP, cosine similarity
**vintage_text** — 384-dim all-MiniLM-L6-v2, cosine similarity

Both collections need `platform` in their payload (currently missing — prerequisite for
cross-source bridge computation):

```python
payload = {
    "product_id": product.id,
    "platform": product.platform,    # ← add this
    "title": product.title,
    "era": product.era,
    "category": product.category,
}
```

---

## Phase Roadmap

### Phase 1: Build the Graph (March 3–28, 2026 — ~75 hours)

**Goal:** 1,000+ enriched items with cross-source bridges computed. Ship web demo.
**Schedule:** 5 days backend (FastAPI + bridge computation), 5 days frontend, 5 days deploy + QA.
**See:** `plans/PHASE_1_IMPLEMENTATION.md` for full step-by-step implementation.

#### Step 1 — Fix Qdrant payloads (1 hour)
Add `platform` field to all Qdrant point payloads so bridge computation can filter
by source. Update `embeddings/generator.py` to include `platform` in upserted payload.
Re-upsert existing points with the missing field.

**File:** `embeddings/generator.py`

#### Step 2 — StyleBridge model (30 min)
Add `StyleBridge` SQLAlchemy model to `storage/database.py`. Run migration.

**File:** `storage/database.py`

#### Step 3 — Bridge computation script (2 hours)
Create `scripts/analysis/compute_bridges.py`.

Structural scoring weights:

| Field             | Weight | Match type   |
|-------------------|--------|--------------|
| fp_category       | 0.20   | exact        |
| silhouette        | 0.15   | exact        |
| neckline          | 0.10   | exact        |
| length            | 0.10   | exact        |
| waistline         | 0.08   | exact        |
| sleeve_length     | 0.07   | exact        |
| nickname          | 0.10   | exact        |
| textile_pattern   | 0.05   | exact        |
| opening_type      | 0.05   | exact        |
| garment_parts     | 0.05   | Jaccard      |
| decorations       | 0.03   | Jaccard      |
| textile_finishing | 0.02   | Jaccard      |

Composite bridge score:
```
# Both items have images:
bridge_score = 0.40 * text_similarity + 0.30 * image_similarity + 0.30 * structural_score

# One or both lack images:
bridge_score = 0.55 * text_similarity + 0.45 * structural_score
```

Only store bridges where `structural_score > 0.15` (at least 1-2 shared attributes).
Keep top 10 per item by bridge_score.

Pipeline:
1. Load all enriched products from Postgres
2. Group by source: historical = {met_museum, smithsonian}, modern = {fashionpedia}
3. For each historical item: Qdrant top-20 by text + top-20 by image → merge candidates
4. Compute structural_score + bridge_score for each candidate
5. Store top-10 as `style_bridge` rows
6. Repeat in reverse (modern → historical)

Estimated output: ~5K–10K bridge rows. Runtime: ~5 min.

**File to create:** `scripts/analysis/compute_bridges.py`

#### Step 4 — Bridge narratives (1 hour)
Add `generate_bridge_narrative()` to `enrichment/claude.py`.

Prompt: fashion historian, one sentence (≤30 words), focus on shared design DNA.
Run on top-3 bridges per item (~1,500 calls, ~$3–5 total).

**File:** `enrichment/claude.py`

#### Step 5 — Bridge query utilities (30 min)
Add to `storage/vector_db.py` (or a new `storage/bridges.py`):

```python
get_modern_echoes(product_id, limit=5)    # historical → modern descendants
get_style_ancestry(product_id, limit=5)  # modern → historical ancestors
get_style_siblings(product_id, limit=10) # structural neighbors regardless of era
```

#### Step 6 — FastAPI backend (2 days)
Replace the planned Node.js API with Python FastAPI — same language as the AI workers,
simpler stack, no inter-process communication needed.

Core endpoints:
```
POST /api/v1/search/text
POST /api/v1/search/image
GET  /api/v1/products/:id
GET  /api/v1/bridges/:id        → { modern_echoes, historical_ancestors, style_siblings }
POST /api/v1/analyze            → Style DNA API (image → structured taxonomy + echoes)
```

**File to create:** `api/main.py`

#### Step 7 — Connect web app to backend (1 day)
Wire `vv-web` (Next.js) to the FastAPI backend. The web app is the demo surface for
the intelligence layer, not a standalone product.

Key views:
- Search (text + image upload)
- Product detail with "Style Ancestry" and "Modern Echoes" panels
- Era/style browse

**Files:** `vv-web/src/app/`

#### Phase 1 success criteria
- [ ] 1,000+ items enriched across Met, Smithsonian, Fashionpedia
- [ ] Cross-source bridges computed and stored
- [ ] Bridge narratives generated for top connections
- [ ] FastAPI backend serving search + bridge endpoints
- [ ] Web app connected and demo-able
- [ ] "Modern echoes" and "style ancestry" visible on product pages

---

### Phase 1.5: Portfolio Launch (March 28–April 4, 2026 — ~45 hours)

**Goal:** Tell the story. Get the project in front of people who can hire or pay.

**Week 4 — Documentation and Content**

Blog post: *"Building a Fashion Knowledge Graph: How I Connected 500 Years of Design History"*
(3,000–4,000 words, 7 sections: Problem → Architecture → Enrichment Pipeline → Bridge Algorithm →
Technical Implementation → What Makes This Different → Lessons Learned)

Portfolio case study for linuxgrrrl.com: overview + challenge + solution + technical highlights +
screenshots of bridge panels. Demonstrates: technical depth, product thinking, AI integration,
full-stack capability.

**Week 5 — Outreach and Positioning**

Update LinkedIn headline, Upwork profile, GitHub README. Submit 10 targeted Upwork proposals
(AI integration, semantic search, ML product, product design). Direct outreach to 5 companies
with Forward Deployed Engineer or AI product roles.

**Success criteria:**
- [ ] Blog post published on linuxgrrrl.com and Dev.to
- [ ] Portfolio case study live
- [ ] LinkedIn + Upwork profiles updated with live demo link
- [ ] GitHub repo pinned with comprehensive README
- [ ] 10 Upwork proposals sent

---

### Phase 2: Style DNA API (Month 3–6)

**Goal:** Expose the intelligence layer as a paid API. First B2B revenue.

**New endpoints:**
```
POST /api/v1/analyze
  Input:  image (base64 or URL)
  Output: {
    taxonomy:          { silhouette, neckline, waistline, length, textile_pattern, ... },
    style:             { era, decade, vibe, style_tags, aesthetic_movements },
    description:       "AI-generated rich description",
    historical_echoes: [ { product_id, bridge_score, shared_attributes, narrative } ]
  }

GET /api/v1/bridges/:product_id
  Output: {
    modern_echoes:        [...],
    historical_ancestors: [...],
    style_siblings:       [...]
  }

GET /api/v1/timeline/:attribute
  Input:  attribute slug (e.g. "a-line", "empire-waist")
  Output: [ { decade, items: [...], prevalence_score } ]
```

**Pricing tiers:**
- Free: 100 calls/month (developer adoption)
- Starter: $99/mo — 5,000 calls
- Pro: $499/mo — 50,000 calls
- Enterprise: custom

**Target first customers:**
1. Resale platforms (Depop, ThredUp, The RealReal) — clearest ROI: better metadata → better search → more GMV
2. Vintage sellers / listing assistants — photo → complete listing
3. Fashion media — reference finder, trend archaeology

**Implementation:**
- API key authentication (simple JWT or opaque tokens, stored in Postgres)
- Per-key rate limiting
- Usage tracking table for billing
- Stripe integration for paid tiers

---

### Phase 3: Scale the Data Layer (Month 6–12)

Add sources to compound the graph's value:

| Source | Items | Access |
|--------|-------|--------|
| V&A Museum | 200K+ costume items | Public REST API |
| Europeana Fashion | 500K+ items | Public API |
| iDesigner | 50K runway images | Scrape or licensing |
| NYPL Digital Collections | 10K+ fashion plates | Public API |
| Etsy live inventory | ∞ | Scrape (careful) |
| Depop live inventory | ∞ | Scrape (careful) |

Each new source creates N new potential bridge connections with all existing items.
Network effect compounds the value of the whole graph.

---

### Phase 4: Trend Oracle (Month 9–15)

Analytics product built on the temporal dimension of the graph:

- Which historical silhouettes are gaining bridge_score momentum with modern items?
- What era references are appearing in runway collections this season?
- Predict which vintage styles will surge in resale value based on bridge patterns

Revenue: annual subscriptions ($5K–50K/yr), competing with WGSN from a data-first angle.

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Image embeddings | CLIP ViT-B-32 (512-dim) | Local inference, zero cost |
| Text embeddings | all-MiniLM-L6-v2 (384-dim) | Local inference, zero cost |
| AI enrichment | Claude Sonnet (Anthropic API) | Best fashion semantics |
| Vector DB | Qdrant (local Docker) | Fast cosine search, payload filtering |
| Relational DB | PostgreSQL + SQLAlchemy | Metadata, bridges, users |
| API backend | FastAPI + Uvicorn | Same language as AI workers, no IPC |
| Web frontend | Next.js 16 + React 19 + TypeScript + Tailwind 4 | Already built |
| Fashion taxonomy | Fashionpedia (294 attributes) | Structured ontology for structural scoring |
| Backend hosting | Railway | Auto-deploy from GitHub, `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| Frontend hosting | Vercel | Zero-config Next.js deploys, `NEXT_PUBLIC_API_URL` env var |

**Dropped from old plan:**
- Node.js / Express API — replaced by FastAPI (simpler, same language)
- React Native mobile app — deprioritized; web first, mobile later if user demand warrants it
- Celery task queue — overkill at current scale; scripts + cron jobs suffice

---

## Cost Model

### Development (current)

| Item | Cost |
|------|------|
| Claude enrichment (1,000 products × $0.02) | ~$20 |
| Claude bridge narratives (~1,500 calls) | ~$5 |
| Infrastructure (local Qdrant, local Postgres) | $0 |
| **Total to Phase 1 complete** | **~$25** |

### Production (post-launch)

| Service | Free tier | When to upgrade |
|---------|-----------|-----------------|
| Railway / Render (FastAPI) | $5–10/mo | Day 1 deploy |
| Neon PostgreSQL | 1GB free | 10K+ products |
| Qdrant Cloud | Self-hosted $0 | 100K+ products |
| Cloudflare R2 | 10GB free | User upload feature |
| **Total small scale** | **$5–15/mo** | — |

Claude API ongoing:
- New enrichment: only for new products ingested
- Bridge narratives: one-time per pair, stored permanently
- Style DNA API calls: pass cost through to paying API customers

---

## What We Are Not Building (Right Now)

| Item | Why not |
|------|---------|
| React Native mobile app | The moat is the graph, not the UI. Web demo is sufficient to prove value and close B2B deals. |
| Node.js API server | FastAPI is simpler and colocated with AI workers. |
| User authentication (Phase 1) | Not needed until API monetization. |
| Real-time web scraping | Legal and operational risk. Dataset-first until B2B revenue justifies it. |
| Celery / task queues | Scripts + cron is enough at current data volume. |

---

## Current Priorities (Week 1: March 3–7)

**Monday–Tuesday — FastAPI skeleton**
1. `api/main.py` with CORS and router wiring
2. `api/models.py` Pydantic schemas
3. `api/search.py` and `api/products.py` stubs with `/health` endpoint

**Wednesday — Bridge computation foundation**
4. `scripts/database/backfill_qdrant_platform.py` — patch existing Qdrant payloads
5. `StyleBridge` SQLAlchemy model in `storage/database.py` — run migration
6. `scripts/analysis/compute_bridges.py` — structural scoring + composite bridge score

**Thursday–Friday — Run bridges + narratives**
7. Execute bridge computation on 1,000-item dataset (~5K–10K rows expected)
8. Add `generate_bridge_narrative()` (standalone function) to `enrichment/claude.py`
9. `scripts/analysis/generate_bridge_narratives.py` — run on bridges with score > 0.5

**Weekend**
10. `storage/bridges.py` — query utilities (`get_modern_echoes`, `get_style_ancestry`, `get_style_siblings`)
11. Wire bridge endpoints in `api/products.py`

---

## Success Metrics

### Phase 1 (Month 1–3)
- 1,000+ enriched items across ≥3 sources
- Cross-source bridges computed (target: 5K–10K bridge rows)
- Demo-able web interface showing style ancestry + modern echoes
- At least one external person says "this is genuinely useful"

### Phase 2 (Month 3–6)
- Style DNA API live with auth + rate limiting
- First paying API customer (any revenue validates the model)
- 10+ B2B outreach conversations initiated

### Phase 3 (Month 6–12)
- 10K+ items in graph
- 3+ data sources integrated
- $10K+ ARR

---

**Owner:** Jen Kim
**Last Updated:** February 2026
**Next Review:** End of Phase 1 (cross-source bridges shipped)
