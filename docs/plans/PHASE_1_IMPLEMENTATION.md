# Phase 1 Implementation Plan
**Fashion Intelligence Platform — Build the Graph**

**Goal:** 1,000+ enriched items, cross-source style bridges computed, FastAPI backend
serving search and bridge endpoints, web demo connected and demo-able.

**Timeline:** March 3–28, 2026 (Weeks 1–3 of 5-week plan)
**Total Effort:** ~60–75 hours (backend + bridges + frontend + deployment)
**Status:** In progress

---

## Current State (What's Already Built)

### Working
- `storage/database.py` — `Product` SQLAlchemy model with full Fashionpedia taxonomy fields
- `storage/vector_db.py` — Qdrant client, `upsert_product()`, `search_similar()`
- `embeddings/generator.py` — CLIP image + MiniLM text embedding pipeline
- `enrichment/claude.py` — `ClaudeEnricher` with `enrich_product()` (full), `enrich_creative_only()` (Fashionpedia items), `build_rich_text()`
- `enrichment/fashionpedia_taxonomy.py` — 294-attribute ontology
- `scripts/embedding_and_enrichment/` — batch embedding + enrichment scripts
- `vv-web/` — Next.js landing page (no backend connection yet)
- ~1,000 products in PostgreSQL across Met Museum, Smithsonian, Fashionpedia

### Known Gaps to Fix Before Bridges
1. Qdrant point payloads are missing the `platform` field — required for cross-source filtering
2. `StyleBridge` table does not exist yet
3. No bridge computation script exists
4. FastAPI backend does not exist
5. Web app is not connected to any backend

---

## This Week's Priorities

### Priority 1 — Fix Qdrant Payloads (1–2 hours)

**Problem:** `embeddings/generator.py` line 120–127 builds the metadata dict passed to
Qdrant, but `platform` is already included there. The issue is that existing points in
Qdrant were stored without `platform` (or with it — needs verification). Bridge
computation requires Qdrant payload filtering by `platform` to find cross-source candidates.

**What to do:**

1. Check whether `platform` is already present in existing Qdrant payloads:
   ```python
   # Quick check in Python shell or notebook
   from storage.vector_db import VectorDB
   vdb = VectorDB()
   results = vdb.client.scroll('vintage_text', limit=3, with_payload=True)
   print(results[0][0].payload)
   ```

2. If `platform` is missing, backfill it. Two options:
   - **Option A (preferred):** Re-run `scripts/embedding_and_enrichment/rebuild_embeddings.py`
     which will re-upsert all points. The payload already includes `platform` in the
     current code, so re-upsert will add it.
   - **Option B (faster, no re-embedding):** Use `set_payload` to patch existing points:
     ```python
     # scripts/database/backfill_qdrant_platform.py
     from storage.vector_db import VectorDB
     from storage.database import SessionLocal, Product
     from qdrant_client.models import SetPayload

     db = SessionLocal()
     vdb = VectorDB()
     products = db.query(Product).filter(Product.embedded_at != None).all()

     for product in products:
         payload_patch = {"platform": product.platform}
         for collection in [vdb.image_collection, vdb.text_collection]:
             try:
                 vdb.client.set_payload(
                     collection_name=collection,
                     payload=payload_patch,
                     points=[product.id]
                 )
             except Exception:
                 pass  # point may not exist in image collection
     db.close()
     ```

**File to create:** `scripts/database/backfill_qdrant_platform.py`

---

### Priority 2 — Add StyleBridge Model (30 min)

Add `StyleBridge` to `storage/database.py` and run migration.

```python
# Add to storage/database.py after the Product class

from sqlalchemy import ForeignKey, UniqueConstraint
import json as json_module

class StyleBridge(Base):
    __tablename__ = 'style_bridges'

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    target_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)

    # Component scores (0.0–1.0)
    text_similarity   = Column(Float, nullable=False)
    image_similarity  = Column(Float, nullable=True)   # null if either item lacks image embedding
    structural_score  = Column(Float, nullable=False)  # weighted Fashionpedia field overlap
    bridge_score      = Column(Float, nullable=False)  # weighted composite, used for ranking

    # What makes them similar
    shared_attributes = Column(Text, nullable=True)    # JSON: {"silhouette": "a-line", "length": "floor length"}
    bridge_type       = Column(String, nullable=True)  # 'historical_to_modern' | 'cross_era' | 'same_era_cross_source'
    bridge_narrative  = Column(Text, nullable=True)    # Claude: one sentence explaining the connection

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('source_id', 'target_id', name='uq_bridge_pair'),
    )
```

Then run:
```bash
python -c "from storage.database import init_db; init_db()"
```

`Base.metadata.create_all()` is additive — it will create the new table without
touching `products`.

**File to modify:** `storage/database.py`

---

### Priority 3 — Build Bridge Computation Script (2–3 hours)

**File to create:** `scripts/analysis/compute_bridges.py`

**Algorithm:**

```
1. Load all enriched products from Postgres (enriched_at IS NOT NULL)
2. Split into:
     historical = platform IN ('met_museum', 'smithsonian')
     modern     = platform IN ('fashionpedia')
3. For each historical item:
   a. Query Qdrant vintage_text  — top 20 modern items (filter: platform=fashionpedia)
   b. Query Qdrant vintage_images — top 20 modern items (filter: platform=fashionpedia)
      (skip if item has no image embedding)
   c. Merge candidate lists → union, ~30–40 unique candidates
   d. For each candidate:
      - compute_structural_score(historical_item, candidate)
      - skip if structural_score < 0.15
      - compute bridge_score
      - record shared_attributes dict
   e. Keep top 10 by bridge_score
   f. Bulk insert as style_bridge rows (use INSERT ... ON CONFLICT DO NOTHING)
4. Repeat in reverse: modern → historical (swap source/target, set bridge_type accordingly)
5. Log summary: N bridges computed, N stored
```

**Structural scoring:**

```python
FIELD_WEIGHTS = {
    'fp_category':       0.20,
    'silhouette':        0.15,
    'neckline':          0.10,
    'length':            0.10,
    'waistline':         0.08,
    'sleeve_length':     0.07,
    'nickname':          0.10,
    'textile_pattern':   0.05,
    'opening_type':      0.05,
}
SET_FIELD_WEIGHTS = {
    'garment_parts':      0.05,   # Jaccard similarity
    'decorations':        0.03,
    'textile_finishing':  0.02,
}

def compute_structural_score(a: Product, b: Product) -> tuple[float, dict]:
    score = 0.0
    shared = {}

    for field, weight in FIELD_WEIGHTS.items():
        val_a = getattr(a, field)
        val_b = getattr(b, field)
        if val_a and val_b and val_a == val_b:
            score += weight
            shared[field] = val_a

    for field, weight in SET_FIELD_WEIGHTS.items():
        raw_a = getattr(a, field)
        raw_b = getattr(b, field)
        set_a = set(json_module.loads(raw_a)) if raw_a else set()
        set_b = set(json_module.loads(raw_b)) if raw_b else set()
        if set_a and set_b:
            intersection = set_a & set_b
            union = set_a | set_b
            jaccard = len(intersection) / len(union)
            score += weight * jaccard
            if intersection:
                shared[field] = list(intersection)

    return score, shared
```

**Composite bridge score:**

```python
def compute_bridge_score(text_sim, image_sim, structural_score):
    if image_sim is not None:
        return 0.40 * text_sim + 0.30 * image_sim + 0.30 * structural_score
    else:
        return 0.55 * text_sim + 0.45 * structural_score
```

**Qdrant cross-source filtering:**

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

modern_filter = Filter(must=[
    FieldCondition(key="platform", match=MatchValue(value="fashionpedia"))
])

results = vdb.client.search(
    collection_name='vintage_text',
    query_vector=query_vector,
    query_filter=modern_filter,
    limit=20
)
```

**Expected output:** 5K–10K bridge rows. Runtime: ~5–10 min for 1,000 items.

---

### Priority 4 — Bridge Narrative Generation (1 hour)

Add `generate_bridge_narrative()` to `enrichment/claude.py` as a **standalone function**
(not a method on `ClaudeEnricher`). Called after bridge computation to annotate the
highest-value connections. The `generate_bridge_narratives.py` script imports it directly:
`from enrichment.claude import generate_bridge_narrative`.

```python
# Standalone function — not a method on ClaudeEnricher
def generate_bridge_narrative(
    source_product: Product,
    target_product: Product,
    shared_attributes: dict
) -> str:
    """Generate one-sentence bridge narrative (≤30 words)"""

    prompt = f"""You are a fashion historian. Write ONE sentence (≤30 words)
    explaining the design connection between these garments:

    Historical item: {source_product.title} ({source_product.era})
    Modern item: {target_product.title}

    Shared design elements: {', '.join(shared_attributes.keys())}

    Focus on the design DNA they share. Be specific and evocative.
    ONE SENTENCE ONLY."""

    response = anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()
```

**Run strategy:** Only generate narratives for bridges where `bridge_score > 0.5`.
That's roughly the top 3 per item. ~1,500 calls × ~$0.003 = ~$4–5 total.

**Script to create:** `scripts/analysis/generate_bridge_narratives.py`

---

### Priority 5 — Bridge Query Utilities (30 min)

Add to `storage/vector_db.py` (or a new `storage/bridges.py`):

```python
from storage.database import SessionLocal, StyleBridge, Product
from sqlalchemy import or_

def get_modern_echoes(product_id: int, limit: int = 5) -> list:
    """For a historical item: find modern items that inherited its design."""
    db = SessionLocal()
    bridges = (
        db.query(StyleBridge, Product)
        .join(Product, Product.id == StyleBridge.target_id)
        .filter(StyleBridge.source_id == product_id)
        .filter(StyleBridge.bridge_type == 'historical_to_modern')
        .order_by(StyleBridge.bridge_score.desc())
        .limit(limit)
        .all()
    )
    db.close()
    return bridges

def get_style_ancestry(product_id: int, limit: int = 5) -> list:
    """For a modern item: find historical items it descended from."""
    db = SessionLocal()
    bridges = (
        db.query(StyleBridge, Product)
        .join(Product, Product.id == StyleBridge.source_id)
        .filter(StyleBridge.target_id == product_id)
        .filter(StyleBridge.bridge_type == 'historical_to_modern')
        .order_by(StyleBridge.bridge_score.desc())
        .limit(limit)
        .all()
    )
    db.close()
    return bridges

def get_style_siblings(product_id: int, limit: int = 10) -> list:
    """Items with the most shared structural attributes, regardless of era."""
    db = SessionLocal()
    bridges = (
        db.query(StyleBridge, Product)
        .join(Product, or_(
            Product.id == StyleBridge.target_id,
            Product.id == StyleBridge.source_id
        ))
        .filter(or_(
            StyleBridge.source_id == product_id,
            StyleBridge.target_id == product_id
        ))
        .filter(Product.id != product_id)
        .order_by(StyleBridge.structural_score.desc())
        .limit(limit)
        .all()
    )
    db.close()
    return bridges
```

---

### Priority 6 — FastAPI Backend Skeleton (1–2 days)

**File to create:** `api/main.py`

Keep it minimal for now — just wire up the search and bridge endpoints using existing
Python modules directly (no Node.js, no inter-process calls).

```
api/
├── main.py          # FastAPI app, routes
├── search.py        # search endpoint logic
├── products.py      # product detail + bridge endpoints
└── models.py        # Pydantic request/response schemas
```

**`api/models.py` — Pydantic schemas:**

```python
from pydantic import BaseModel
from typing import List, Optional, Dict

class ProductResponse(BaseModel):
    id: int
    title: str
    platform: str
    era: Optional[str]
    category: Optional[str]
    style_tags: Optional[List[str]]
    primary_image: Optional[str]
    ai_description: Optional[str]

class SearchResponse(BaseModel):
    results: List[ProductResponse]
    total: int

class StyleBridgeResponse(BaseModel):
    id: int
    source_id: int
    target_id: int
    bridge_score: float
    structural_score: float
    shared_attributes: Dict[str, str]
    bridge_narrative: Optional[str]
    bridge_type: str
    product: ProductResponse

class BridgeResponse(BaseModel):
    modern_echoes: List[StyleBridgeResponse]
    historical_ancestors: List[StyleBridgeResponse]
    style_siblings: List[StyleBridgeResponse]
```

**Core endpoints for Phase 1:**

```python
# api/main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from embeddings.generator import EmbeddingGenerator
from storage.vector_db import VectorDB
from storage.database import SessionLocal, Product

app = FastAPI(title="Vintage Vestige API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict to your domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# POST /api/v1/search/text
# POST /api/v1/search/image
# GET  /api/v1/products/{id}
# GET  /api/v1/bridges/{id}      → { modern_echoes, historical_ancestors, style_siblings }
```

Add a `/health` endpoint — trivial, needed for deployment monitoring and smoke-testing:

```python
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
```

**Run:**
```bash
uvicorn api.main:app --reload --port 8000
```

---

### Priority 7 — Complete and Connect Web App (2–3 days)

**Current state of `vv-web`** (audited February 2026):

| File | Status |
|------|--------|
| `src/components/ui/` (Button, Input, Card, Badge, index.ts) | ✅ Complete |
| `src/lib/utils.ts` (`cn`, `formatPrice`, `debounce`) | ✅ Complete |
| `src/lib/constants.ts` (`API_BASE_URL`, `DEFAULT_SEARCH_LIMIT`) | ✅ Complete |
| `src/lib/api.ts` (`searchByText`, `searchByImage`, `getProduct`, `getFilters`) | ✅ Complete — uses native `fetch`, `NEXT_PUBLIC_API_URL` already wired |
| `src/types/index.ts` (Product, SearchResponse, filters) | ✅ Complete — matches backend schema |
| `src/app/layout.tsx` (Playfair + Inter fonts, metadata) | ✅ Complete |
| `src/app/globals.css` | ✅ Complete |
| `src/app/page.tsx` | ⚠️ Hero + How-it-works sections exist, CTA buttons not yet wired |
| `src/components/layout/Header.tsx` | ❌ Empty stub (0 bytes) |
| `src/components/layout/Footer.tsx` | ❌ Empty stub (0 bytes) |
| `src/components/search/SearchBar.tsx` | ❌ Empty stub (0 bytes) |
| `src/components/search/ImageUpload.tsx` | ❌ Empty stub (0 bytes) |
| `src/components/search/ProductCard.tsx` | ❌ Empty stub (0 bytes) |
| `src/lib/store.ts` | ❌ Missing — no state management yet |
| `src/app/search/page.tsx` | ❌ Missing |
| `src/app/products/[id]/page.tsx` | ❌ Missing |

The design system (colors, typography, UI primitives) and API layer are done. The
remaining work is implementing the stub components and new pages.

**Step 7a — Fill stub components (1 day)**

`src/components/search/SearchBar.tsx` — text input with debounced submit, calls `searchByText()`.
Uses existing `Input`, `Button` from the UI library and `debounce` from `utils.ts`.

`src/components/search/ImageUpload.tsx` — drag-and-drop file input with preview, calls
`compressImage()` before passing blob to `searchByImage()`. Compression is mandatory:
raw images are 3–10MB and will hit FastAPI's default body limit.

```typescript
// vv-web/src/lib/compress-image.ts  ← create this first
export async function compressImage(file: File, maxPx = 1024, quality = 0.85): Promise<Blob> {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      const scale = Math.min(1, maxPx / Math.max(img.width, img.height))
      const canvas = document.createElement('canvas')
      canvas.width = img.width * scale
      canvas.height = img.height * scale
      canvas.getContext('2d')!.drawImage(img, 0, 0, canvas.width, canvas.height)
      canvas.toBlob((blob) => resolve(blob!), 'image/jpeg', quality)
    }
    img.src = URL.createObjectURL(file)
  })
}
```

`src/components/search/ProductCard.tsx` — displays product image, title, era badge,
similarity score. Uses existing `Card`, `Badge` from UI library. Links to
`/products/[id]`.

`src/components/layout/Header.tsx` — sticky header with logo, nav links (Search,
Explore, Timeline), saved-items count badge. Spec is in `VINTAGE_VESTIGE_WEEK1_IMPLEMENTATION.md`.

`src/components/layout/Footer.tsx` — links + copyright. Spec in same file above.

`src/lib/store.ts` — Zustand store for search results, loading state, saved products.
Spec in `VINTAGE_VESTIGE_WEEK1_IMPLEMENTATION.md`. Install: `npm install zustand`.

**Step 7b — Add `getBridges` to `api.ts` (15 min)**

The existing `api.ts` has `searchByText`, `searchByImage`, `getProduct`, `getFilters`
but is missing the bridges endpoint. Add:

```typescript
// append to vv-web/src/lib/api.ts
export async function getBridges(id: number) {
  const res = await fetch(`${API_BASE_URL}/api/v1/bridges/${id}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
```

Also add the `BridgeResponse` type to `src/types/index.ts`:

```typescript
export interface StyleBridge {
  id: number
  source_id: number
  target_id: number
  bridge_score: number
  structural_score: number
  shared_attributes: Record<string, string>
  bridge_narrative: string | null
  bridge_type: string
  product: Product  // joined product data
}

export interface BridgeResponse {
  modern_echoes: StyleBridge[]
  historical_ancestors: StyleBridge[]
  style_siblings: StyleBridge[]
}
```

**Step 7c — Create new pages and bridge component (1 day)**

`src/components/bridges/BridgeCard.tsx` — displays a single bridge connection.
Layout: 3-column grid (image thumbnail | title + era badge + narrative italic quote +
shared attribute badges + "X% style match"). Used in the product detail page.

`src/app/search/page.tsx` — results grid using `ProductCard`. Reads query from URL
params (`?q=...&mode=text|image`). Calls `searchByText` or `searchByImage` on mount.

`src/app/products/[id]/page.tsx` — product detail with:
- Full image, title, era, ai_description, style_tags
- "Style Ancestry" section — calls `getBridges(id)` → renders `historical_ancestors`
- "Modern Echoes" section — renders `modern_echoes`
- Each bridge card shows `bridge_narrative` and `shared_attributes` badges

`src/app/about/page.tsx` — project overview page. Content: what Vintage Vestige is
(knowledge graph), how it works (AI enrichment → CLIP embeddings → style bridges),
data sources (Met, Smithsonian, Fashionpedia). Used by the Header nav link.

`src/app/page.tsx` — wire the CTA buttons to navigate to `/search?mode=image` and
`/search?mode=text`. The hero copy and layout are already correct.

**Note:** No auth required for Phase 1 — public read-only demo. `NEXT_PUBLIC_API_URL`
in `.env.local` already switches between local and deployed backend.

---

### Priority 8 — Deploy (Week 3)

**Backend → Railway**

Create `railway.json` at the project root:

```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn api.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Set Railway environment variables: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `QDRANT_URL`.
Run `init_db()` on first deploy to create tables. Verify `/health` returns `{"status": "ok"}`.

**Frontend → Vercel**

Connect GitHub repo to Vercel. Set `NEXT_PUBLIC_API_URL=https://your-api.railway.app`.
Deploy. Test end-to-end: search → product detail → bridge panels.

**QA checklist (12 items):**
- [ ] `/health` endpoint returns ok
- [ ] Text search returns results
- [ ] Image upload works (test 5 images)
- [ ] Product detail pages load
- [ ] Bridge panels show related items
- [ ] Bridge narratives display correctly
- [ ] Shared attributes badges show
- [ ] Navigation works across all pages
- [ ] Mobile responsive (test on phone)
- [ ] No console errors
- [ ] Images load properly
- [ ] Error states handled gracefully

**Sample test queries:** "romantic edwardian dress", "dark academia aesthetic",
"empire waist gown", "art nouveau evening wear", "victorian bustle dress"

---

## Phase 1 Success Criteria

- [ ] `platform` present in all Qdrant payloads
- [ ] `style_bridges` table created and populated
- [ ] 5,000+ bridge rows computed across Met × Fashionpedia and Smithsonian × Fashionpedia
- [ ] Bridge narratives generated for bridges with `bridge_score > 0.5`
- [ ] FastAPI serving `/search/text`, `/search/image`, `/products/:id`, `/bridges/:id`
- [ ] Web demo showing style ancestry and modern echoes on product pages
- [ ] At least one person outside the project says "this is genuinely useful"

---

## File Map — What to Create / Modify

| File | Action | Priority |
|------|--------|----------|
| `scripts/database/backfill_qdrant_platform.py` | Create | 1 |
| `storage/database.py` | Add `StyleBridge` model | 2 |
| `scripts/analysis/compute_bridges.py` | Create | 3 |
| `enrichment/claude.py` | Add `generate_bridge_narrative()` | 4 |
| `scripts/analysis/generate_bridge_narratives.py` | Create | 4 |
| `storage/bridges.py` | Create (query utilities) | 5 |
| `api/main.py` | Create | 6 |
| `api/search.py` | Create | 6 |
| `api/products.py` | Create | 6 |
| `api/models.py` | Create | 6 |
| `vv-web/src/lib/api.ts` | Modify — add `getBridges()` | 7 |
| `vv-web/src/types/index.ts` | Modify — add `StyleBridge`, `BridgeResponse` types | 7 |
| `vv-web/src/lib/compress-image.ts` | Create | 7 |
| `vv-web/src/lib/store.ts` | Create (Zustand search + saved state) | 7 |
| `vv-web/src/components/search/SearchBar.tsx` | Implement (stub exists) | 7 |
| `vv-web/src/components/search/ImageUpload.tsx` | Implement (stub exists) | 7 |
| `vv-web/src/components/search/ProductCard.tsx` | Implement (stub exists) | 7 |
| `vv-web/src/components/layout/Header.tsx` | Implement (stub exists) | 7 |
| `vv-web/src/components/layout/Footer.tsx` | Implement (stub exists) | 7 |
| `vv-web/src/components/bridges/BridgeCard.tsx` | Create | 7 |
| `vv-web/src/app/search/page.tsx` | Create | 7 |
| `vv-web/src/app/products/[id]/page.tsx` | Create (with bridge panels) | 7 |
| `vv-web/src/app/about/page.tsx` | Create (project overview page) | 7 |
| `vv-web/src/app/page.tsx` | Modify — wire CTA buttons to `/search` routes | 7 |
| `railway.json` | Create (Railway deployment config) | 8 |

---

## Cost Estimate for Phase 1 Completion

| Task | Claude calls | Est. cost |
|------|-------------|-----------|
| Remaining enrichment (to reach 1,000 fully enriched) | ~200 | ~$4 |
| Bridge narratives (top bridges, score > 0.5) | ~1,500 | ~$5 |
| **Total** | | **~$9** |

Embedding generation (CLIP + MiniLM): $0 — local inference.

---

## Upcoming Phases (Summary)

### Phase 2 — Style DNA API (Month 3–6)
Expose the intelligence layer as a paid B2B API. The core product for resale platforms,
fashion brands, and media.

**New endpoints:**
- `POST /api/v1/analyze` — image in, full taxonomy + historical echoes out
- `GET /api/v1/timeline/:attribute` — how a silhouette or pattern evolved across decades

**Monetization:**
- API key auth + usage tracking
- Stripe integration for paid tiers ($99/mo → $499/mo → enterprise)
- Target first customers: resale platforms (Depop, ThredUp) and vintage sellers

**Data target:** 1,000 → 5,000 enriched items

### Phase 3 — Scale the Data Layer (Month 6–12)
Add museum and marketplace sources to compound the graph's value. Each new source
creates N new bridge connections with all existing items.

**Sources to add (in priority order):**
1. V&A Museum (public REST API, 200K+ costume items)
2. Europeana Fashion (500K+ items, public API)
3. iDesigner runway images (designer → historical DNA)
4. NYPL Digital Collections

**Data target:** 5,000 → 50,000+ enriched items

### Phase 4 — Trend Oracle (Month 9–15)
Analytics product built on the temporal dimension of the knowledge graph.

- Which historical silhouettes are gaining bridge_score momentum?
- What era references are appearing in this season's runway collections?
- Which vintage styles will surge in resale value based on bridge patterns?

Competes with WGSN ($30K+/yr) from a data-first angle. Annual subscriptions
($5K–50K/yr per customer).
