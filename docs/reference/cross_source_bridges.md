# Cross-Source Style Bridges — Implementation Plan

## What We're Building
A system that connects historical fashion items (Met Museum, Smithsonian) to modern
items (Fashionpedia) based on structural similarity, visual similarity, and semantic
similarity. This is the core differentiator of Vintage Vestige: "find the modern
version of this historical garment."

## Why It Matters
- Users searching "dark academia" should discover Victorian riding jackets they never
  knew existed
- Users browsing an 1860s ballgown should see modern mermaid gowns that inherited
  its silhouette
- Bridges create the "time travel" experience that makes Vintage Vestige unique

---

## Phase 1: Database Schema

### New table: `style_bridges`

```sql
CREATE TABLE style_bridges (
    id SERIAL PRIMARY KEY,

    -- The two items being connected
    source_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    target_id INTEGER REFERENCES products(id) ON DELETE CASCADE,

    -- Similarity scores (0.0 to 1.0)
    text_similarity FLOAT NOT NULL,       -- cosine similarity of text embeddings
    image_similarity FLOAT,               -- cosine similarity of CLIP embeddings (nullable — some items lack images)
    structural_score FLOAT NOT NULL,      -- % of shared Fashionpedia taxonomy fields
    bridge_score FLOAT NOT NULL,          -- weighted composite score

    -- What makes them similar
    shared_attributes JSONB,              -- {"silhouette": "a-line", "length": "floor length", ...}
    bridge_type VARCHAR(50),              -- 'historical_to_modern', 'cross_era', 'same_era_cross_source'

    -- Optional Claude-generated narrative
    bridge_narrative TEXT,                -- "This 1860s bustle gown shares the dramatic silhouette..."

    -- IIT 4.0 future-proofing (nullable — populated post-MVP)
    phi_score FLOAT,                     -- Φ integration score for this bridge pair
    cnn_structural_score FLOAT,          -- structural score using CNN-verified attributes

    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX idx_bridges_source ON style_bridges(source_id);
CREATE INDEX idx_bridges_target ON style_bridges(target_id);
CREATE INDEX idx_bridges_score ON style_bridges(bridge_score DESC);
CREATE INDEX idx_bridges_type ON style_bridges(bridge_type);

-- Prevent duplicate pairs
CREATE UNIQUE INDEX idx_bridges_pair ON style_bridges(source_id, target_id);
```

### Add to SQLAlchemy model (storage/database.py)

```python
class StyleBridge(Base):
    __tablename__ = 'style_bridges'

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    target_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    text_similarity = Column(Float, nullable=False)
    image_similarity = Column(Float, nullable=True)
    structural_score = Column(Float, nullable=False)
    bridge_score = Column(Float, nullable=False)
    shared_attributes = Column(Text, nullable=True)  # JSON
    bridge_type = Column(String, nullable=True)
    bridge_narrative = Column(Text, nullable=True)
    # IIT 4.0 future-proofing (nullable — populated post-MVP)
    phi_score = Column(Float, nullable=True)             # Φ integration score for this bridge pair
    cnn_structural_score = Column(Float, nullable=True)  # structural score using CNN-verified attributes
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Files to modify:** `storage/database.py`

---

## Phase 2: Structural Similarity Engine

### New file: `scripts/analysis/compute_bridges.py`

Core logic for computing structural overlap between two items using their
Fashionpedia taxonomy fields.

### Structural scoring algorithm

Compare taxonomy fields between two products. Each match adds to the score:

| Field            | Weight | Match Type    |
|------------------|--------|---------------|
| fp_category      | 0.20   | exact         |
| silhouette       | 0.15   | exact         |
| neckline         | 0.10   | exact         |
| length           | 0.10   | exact         |
| waistline        | 0.08   | exact         |
| sleeve_length    | 0.07   | exact         |
| nickname         | 0.10   | exact         |
| textile_pattern  | 0.05   | exact         |
| opening_type     | 0.05   | exact         |
| garment_parts    | 0.05   | Jaccard (set) |
| decorations      | 0.03   | Jaccard (set) |
| textile_finishing | 0.02  | Jaccard (set) |

Structural score = sum of weighted matches. Range: 0.0 to 1.0.

Only items with structural_score > 0.15 are worth bridging (they share at least
1-2 meaningful attributes).

### Composite bridge score

```
bridge_score = 0.40 * text_similarity
             + 0.30 * image_similarity (or 0 if unavailable)
             + 0.30 * structural_score
```

Normalize so items without image similarity aren't penalized:
- If both have images: use weights above
- If one or both lack images: redistribute to 0.55 text + 0.45 structural

**Files to create:** `scripts/analysis/compute_bridges.py`

---

## Phase 3: Bridge Computation Pipeline

### Algorithm (batch process)

```
1. Load all enriched products from Postgres
2. Group by platform: historical = {met_museum, smithsonian}, modern = {fashionpedia}
3. For each historical item:
   a. Query Qdrant for top-20 most similar modern items (text embedding)
   b. Query Qdrant for top-20 most similar modern items (image embedding)
   c. Merge candidate lists (union of both, ~30-40 unique candidates)
   d. For each candidate:
      - Compute structural_score from taxonomy field overlap
      - Compute composite bridge_score
      - Record shared_attributes dict
   e. Keep top 10 candidates by bridge_score
   f. Store as style_bridge rows
4. Repeat in reverse: for each modern item, find top-10 historical matches
5. Optional: batch Claude calls for bridge_narrative on top-3 per item
```

### Performance considerations

- Current scale: ~500 historical × ~500 modern = 250K potential pairs
- Qdrant narrows to ~40 candidates per item via vector search
- Actual comparisons: 500 × 40 = 20K structural computations (fast, in-memory)
- Final stored bridges: ~5K-10K rows
- Estimated time: ~5 min (excluding optional Claude narratives)

### Qdrant filtering

Use payload filters to restrict search to cross-source items:

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Historical item searching for modern matches
modern_filter = Filter(must=[
    FieldCondition(
        key="platform",   # need to add platform to Qdrant payloads
        match=MatchValue(value="fashionpedia")
    )
])
```

**Prerequisite:** Add `platform` to Qdrant point payloads in the enrichment
pipeline (currently not stored there).

---

## Phase 4: Bridge Narratives (Optional, Claude-powered)

For the highest-scoring bridges (top 3 per item), generate a human-readable
explanation of why they're connected.

### Prompt template

```
You're a fashion historian. These two items are connected across time:

HISTORICAL: {title}, {era}, {culture}
  Attributes: {silhouette}, {neckline}, {material}, {textile_pattern}

MODERN: {title}
  Attributes: {silhouette}, {neckline}, {material}, {textile_pattern}

SHARED: {shared_attributes}

Write one sentence (max 30 words) explaining the style connection
between these items. Focus on the design DNA they share.
```

### Cost estimate
- ~500 items × 3 narratives = 1,500 Claude calls
- Short prompt + short response (~100 tokens each)
- Estimated cost: ~$3-5

**Files to modify:** `enrichment/claude.py` (add `generate_bridge_narrative` method)

---

## Phase 5: Query API

### New utility functions (can live in storage/vector_db.py or a new file)

```python
def get_modern_echoes(product_id, limit=5):
    """For a historical item, find its modern descendants."""
    return db.query(StyleBridge).filter(
        StyleBridge.source_id == product_id,
        StyleBridge.bridge_type == 'historical_to_modern'
    ).order_by(StyleBridge.bridge_score.desc()).limit(limit).all()

def get_style_ancestry(product_id, limit=5):
    """For a modern item, find its historical ancestors."""
    return db.query(StyleBridge).filter(
        StyleBridge.target_id == product_id,
        StyleBridge.bridge_type == 'historical_to_modern'
    ).order_by(StyleBridge.bridge_score.desc()).limit(limit).all()

def get_style_siblings(product_id, limit=10):
    """Items with the most shared attributes regardless of era."""
    bridges = db.query(StyleBridge).filter(
        or_(
            StyleBridge.source_id == product_id,
            StyleBridge.target_id == product_id
        )
    ).order_by(StyleBridge.structural_score.desc()).limit(limit).all()
    return bridges
```

---

## Implementation Order

| Step | What | Effort | Dependencies |
|------|------|--------|-------------|
| 1    | Add StyleBridge model + migration | 15 min | None |
| 2    | Add `platform` to Qdrant payloads | 10 min | Enrichment pipeline must finish |
| 3    | Build compute_bridges.py | 45 min | Steps 1-2 |
| 4    | Run bridge computation | ~5 min runtime | Step 3 |
| 5    | Add bridge_narrative generation | 20 min | Step 4 |
| 6    | Run narrative generation | ~10 min runtime | Step 5 |
| 7    | Add query utility functions | 15 min | Step 4 |
| 8    | Test with sample queries | 10 min | Step 7 |

Total implementation: ~2 hours
Total compute: ~15 min (+ Claude narrative time)

---

## What This Unlocks (Future UI Features)

- **"Modern Echoes"** — every museum piece shows modern items that inherited its design
- **"Style Ancestry"** — every modern item traces back to historical inspirations
- **"Time Travel Search"** — "show me the 2020s version of this 1920s dress"
- **"Design DNA"** — shared attribute badges: "Both share: A-line silhouette, floor length, empire waist"
- **Style timeline** — group bridges by decade to visualize how a silhouette evolved
