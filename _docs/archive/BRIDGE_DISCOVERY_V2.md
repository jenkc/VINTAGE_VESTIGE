# Bridge Discovery V2 — Full Pipeline Redesign

## Problem

The current pipeline runs 3 passes that are really 1 strategy applied 3 times: vector similarity with different SQL WHERE clauses. This biases all bridge discovery toward items that *describe* similarly (embedding proximity) rather than items that *relate* interestingly.

The most compelling bridges — contrast, cross-cultural comparison, "same question different answer," independent invention — live in regions of the embedding space that vector search never reaches.

## Current Pipeline (V1): 3 passes, all vector-first

```
For each product:
  Pass 1 (open):           top-20 nearest by embedding → score → keep 5
  Pass 2 (cross-category): top-10 nearest, different category → score → keep 2
  Pass 3 (cross-culture):  top-10 nearest, different culture → score → keep 2
```

Passes 2 and 3 are the same algorithm as Pass 1 with a filter. They don't ask a different question — they apply a different constraint to the same question ("who's nearby in embedding space?"). Cross-cultural bridges found this way are still biased toward items that describe similarly, just filtered to different cultures.

## Redesigned Pipeline (V2): 4 passes, each asking a different question

Each pass uses a different **candidate selection strategy** — the entry point for finding pairs. Every pass shares the same structural scoring and bridge insertion logic.

```
Pass 1: Similarity   — "What sounds/looks like this?"      → vector proximity
Pass 2: Opposition   — "What argues against this?"         → opposing core_vibes
Pass 3: Shared Purpose — "Who answers the same question?"  → shared social_function
Pass 4: Parallel Form — "Who arrived at the same shape?"   → shared (category, silhouette)
```

Cross-category and cross-culture coverage happens **naturally** within passes 2-4 rather than as separate vector searches:
- Opposition crosses categories (volume arguments happen across dresses and coats)
- Shared purpose crosses cultures (wedding garments exist everywhere)
- Parallel form crosses eras (A-line silhouettes appear across centuries)

---

## Pass 1: Similarity (vector-first)

**Question:** "What sounds/looks like this item?"
**Finds:** Affinity and resonance bridges — items that genuinely echo each other.
**Entry point:** pgvector cosine distance (text + image embeddings).

**Algorithm:**

```
For each product:
  1. Fetch top-K nearest neighbors by text embedding (pgvector <=>)
     If image embedding exists, also fetch top-K by image embedding
  2. Merge and deduplicate candidate lists
  3. For each candidate:
     - Compute structural_score (12-field weighted match)
     - Compute bridge_score: 0.40*text_sim + 0.30*image_sim + 0.30*structural
       (or 0.55*text + 0.45*structural if no image)
     - Skip if bridge_score < min_bridge
  4. Keep top N bridges per product
  5. Insert with ON CONFLICT DO NOTHING
```

**Parameters:**

| Param | Value | Notes |
|-------|-------|-------|
| top_k | 30 | Candidates per vector search (up from 20 — cast wider net) |
| top_n | 5 | Bridges to keep per product |
| min_structural | 0.05 | Floor for structural score |
| min_bridge | 0.30 | Floor for composite bridge score |

**What changes from V1:** Drop the cross-category and cross-culture sub-passes. Increase top_k from 20 to 30 to compensate — the single pass now has a slightly wider candidate window. This pass no longer tries to force cross-category or cross-culture bridges through vector proximity; those are better handled by passes 3 and 4.

**Bridge type assignment:** Temporal classification based on era/decade distance:
- `transmission` — different eras, midpoints 40+ years apart
- `continuation` — same era, decades 20+ years apart
- No type override (was `cross_category`/`cross_culture` in V1 — now handled by the classifier's `crossing_type` dimension)

---

## Pass 2: Opposition (vibe-first)

**Question:** "What makes the opposing argument on the same aesthetic axis?"
**Finds:** Contrast bridges — items with opposing vibes but enough shared structural DNA that the opposition is a conversation, not noise.
**Entry point:** Cross-join of opposing `core_vibes` groups. No vector search.

**The 9 opposition pairs:**

```python
OPPOSITION_PAIRS = [
    # (vibe_a, vibe_b, axis)
    ("Exaggerated Volume",          "Column Minimalism",          "volume"),
    ("Constructed Armor",           "Draped Fluidity",            "volume"),
    ("Constructed Armor",           "Body Liberation",            "volume"),
    ("Maximalist Ornament",         "Austere Restraint",          "ornament"),
    ("Transparency and Revelation", "Body Concealment",           "ornament"),
    ("Body Liberation",             "Body Transformation",        "body"),
    ("Body Display",                "Body Concealment",           "body"),
    ("Transgressive Subversion",    "Elite Distinction",          "register"),
    ("Pastoral Naturalism",         "Ceremonial Formalism",       "register"),
]
```

**Algorithm:**

```
1. Build vibe index: {vibe_term: set(product_ids)} from core_vibes JSON arrays
2. For each opposition pair (vibe_a, vibe_b, axis):
     products_a = vibe_index[vibe_a]
     products_b = vibe_index[vibe_b]
3. For each (a, b) in products_a x products_b:
     - Enforce canonical ordering (a.id < b.id)
     - Skip if bridge already exists (check existing_pairs set)
     - Compute structural_score(a, b)
     - Skip if structural_score < structural_gate
     - Fetch text_sim and image_sim from embeddings (lazy — only if structural passes)
     - Compute bridge_score: 0.20*text + 0.20*image + 0.60*structural
       (structural dominates — the opposition IS the connection, form is the evidence)
4. Per opposition pair: sort by bridge_score, keep top N
5. Insert with ON CONFLICT DO NOTHING
6. Tag shared_attributes with discovery method + opposition pair + axis
```

**Parameters:**

| Param | Value | Notes |
|-------|-------|-------|
| structural_gate | 0.3 | Lower than normal — opposition itself justifies the bridge |
| top_per_pair | 20 | Best bridges per opposition pair |
| min_bridge | 0.20 | Very low — even modest structural overlap matters for contrasts |

**Scale check:** If each vibe averages ~200 products, each pair generates ~40K candidates. 9 pairs = ~360K. But structural_score computation is cheap (dict lookups + Jaccard), and the gate at 0.3 cuts most pairs within microseconds. The expensive part (fetching embeddings for text/image sim) only runs on candidates that pass the structural gate.

**Scoring weight rationale:** For contrast bridges, structural similarity is the whole point. Two items need to share enough form (silhouette, category, construction) for their vibe opposition to be a *conversation* rather than random difference. Text/image sim matters less because by definition these items describe differently — that's why vector search misses them.

**shared_attributes example:**

```json
{
  "discovery": "opposition",
  "opposition_pair": "Exaggerated Volume <-> Column Minimalism",
  "axis": "volume",
  "fp_category": "dress",
  "silhouette": "A-line",
  ...other matching structural fields...
}
```

---

## Pass 3: Shared Purpose (function-first)

**Question:** "Who else answers the same social question, from a different context?"
**Finds:** Cross-cultural and cross-temporal comparison bridges. "Same question, different answer."
**Entry point:** Shared `social_function` values. No vector search.

**Algorithm:**

```
1. Build function index: {function: set(product_ids)} from social_function JSON arrays
2. For each function with >= 2 products:
     products = function_index[function]
3. Generate candidate pairs that cross at least one context boundary:
     a) Different culture (cross-cultural comparison)
     b) Different era with midpoints 40+ years apart (temporal transmission)
     c) Different fp_category group (structural divergence within same purpose)
   Must satisfy at least ONE of (a), (b), (c).
   Skip pairs where culture + era + category are all the same (too similar).
4. For each candidate pair:
     - Enforce canonical ordering
     - Skip if bridge already exists
     - Compute structural_score(a, b)
     - Fetch text_sim, image_sim
     - Compute bridge_score: 0.35*text + 0.25*image + 0.40*structural
       (structural slightly elevated — shared purpose + structural overlap = strong bridge)
     - No minimum structural gate (zero structural overlap can still be interesting
       for "completely different answers" — but these will score lower naturally)
5. Per function: sort by bridge_score, keep top N
6. Insert, tag shared_attributes with function + discovery method
```

**Parameters:**

| Param | Value | Notes |
|-------|-------|-------|
| top_per_function | 15 | Best bridges per social function |
| min_bridge | 0.25 | Low threshold — the shared function provides the story |

**Scale check:** Largest functions (ceremony, status-signaling) might have 500+ products = ~125K pairs before boundary filtering. The boundary filter ("must cross culture OR era OR category") cuts this dramatically — most same-function products from the same museum collection share culture and era.

**What this replaces from V1:** The cross-culture pass (V1 pass 3) was trying to find this, but starting from vector proximity. A Japanese wedding kimono and a Victorian bridal gown don't have similar embeddings — vector search won't pair them. This pass finds them directly because they share `["wedding"]` in `social_function`.

**shared_attributes example:**

```json
{
  "discovery": "function_match",
  "shared_function": "wedding",
  "boundary_crossed": "cross_culture",
  "fp_category": "dress",
  ...other matching structural fields...
}
```

---

## Pass 4: Parallel Form (structure-first)

**Question:** "Who independently arrived at the same shape?"
**Finds:** Structural doppelgangers — items with shared form from completely different contexts.
**Entry point:** Shared `(fp_category, silhouette)`. No vector search.

**Algorithm:**

```
1. Group products by (fp_category, silhouette) — the two heaviest structural fields
   Skip groups with < 3 products (too small to be interesting)
2. Within each group, generate candidate pairs that cross context:
     - Different era (any era distance)
     - OR different culture
     - OR different platform
   Must satisfy at least ONE. Prioritize pairs that cross multiple boundaries.
3. For each candidate pair:
     - Enforce canonical ordering
     - Skip if bridge already exists
     - Compute full structural_score(a, b) — expect high scores (>0.5)
     - Fetch text_sim, image_sim
     - Base bridge_score: 0.25*text + 0.25*image + 0.50*structural
     - Discovery bonus: if text_sim < 0.4, add +0.10 (cap at 1.0)
       (items that describe very differently despite matching structurally
        are "independent inventions" — the most interesting parallels)
4. Per (category, silhouette) group: sort by bridge_score, keep top N
5. Insert, tag shared_attributes with matching fields + discovery method
```

**Parameters:**

| Param | Value | Notes |
|-------|-------|-------|
| top_per_group | 10 | Best bridges per structural group |
| min_structural | 0.40 | Higher than normal — structural match is the premise |
| min_bridge | 0.30 | Standard threshold |
| discovery_bonus | +0.10 | Reward for low text similarity (independent invention) |
| bonus_threshold | text_sim < 0.4 | Below this, items describe very differently |

**Scale check:** Groups bounded by `(fp_category x silhouette)` cardinality. ~15 categories x ~10 silhouettes = ~150 groups max. Most groups are 10-50 items. Context-crossing filter further reduces pairs. Total candidates: low thousands.

**The discovery bonus:** This is the key insight of this pass. A Japanese kimono coat and a French redingote that share silhouette, length, and opening type but use completely different language — that's a discovery. High structural score + low text similarity = independent invention of the same form. The bonus makes these rank above pairs that are both structurally AND textually similar (which Pass 1 already finds).

**What this replaces from V1:** The cross-category pass (V1 pass 2) was trying to find structural parallels across categories, but starting from vector proximity. Items with similar form but different descriptions get missed. This pass finds them by starting from shared form.

**shared_attributes example:**

```json
{
  "discovery": "structural_parallel",
  "matching_fields": ["fp_category", "silhouette", "length", "waistline"],
  "text_sim_bonus": true,
  "independent_invention": true,
  ...other matching structural fields...
}
```

---

## Shared Infrastructure

### Scoring (extract to `analysis/bridge_scoring.py`)

Functions shared across all passes:

```python
# From current compute_bridges.py — extract, don't duplicate:
compute_structural_score(a, b, product_map)  # 12-field weighted match
_get_category_group(fp_category)              # category → group mapping
parse_decade_to_year(decade_str)              # "1920s" → 1920
shares_cross_cultural_field(a, b)             # substance gate
compute_text_similarity(vec_a, vec_b)         # cosine sim from pgvector strings
compute_image_similarity(vec_a, vec_b)        # cosine sim from pgvector strings

# New:
compute_bridge_score(text_sim, image_sim, structural, weights)  # configurable weights
classify_temporal(era_a, era_b, decade_a, decade_b)             # transmission/continuation/contemporary
```

### Bridge insertion

All passes use the same insert logic:

```python
def insert_bridge(db, bridge_dict, existing_pairs):
    """Insert a bridge with ON CONFLICT DO NOTHING. Returns True if inserted."""
    pair = (bridge_dict['source_id'], bridge_dict['target_id'])
    if pair in existing_pairs:
        return False
    stmt = pg_insert(StyleBridge.__table__).values(**bridge_dict)
    stmt = stmt.on_conflict_do_nothing(constraint='uq_bridge_pair')
    result = db.execute(stmt)
    if result.rowcount:
        existing_pairs.add(pair)
        return True
    return False
```

### Existing pair tracking

Load all existing `(source_id, target_id)` pairs at startup to avoid redundant scoring:

```python
existing_pairs = set()
rows = db.execute(text("SELECT source_id, target_id FROM style_bridges")).fetchall()
for r in rows:
    existing_pairs.add((r[0], r[1]))
```

This is checked before scoring candidates in every pass — avoids wasting compute on pairs that already have bridges.

---

## File Structure

```
analysis/
  bridge_scoring.py          # NEW — shared scoring functions (extracted from compute_bridges.py)
  compute_bridges.py         # UPDATED — Pass 1 only (vector similarity), imports from bridge_scoring
  compute_bridges_v2.py      # NEW — Passes 2-4 (opposition, function, structural)
  bridge_queries.py          # Unchanged — API query helpers
  generate_narratives.py     # Unchanged — works on all bridges regardless of discovery method
```

### `compute_bridges.py` changes

- Remove cross-category and cross-culture passes (lines defining passes 2 and 3)
- Import scoring functions from `bridge_scoring.py` instead of defining inline
- Increase `top_k` from 20 to 30
- Keep resume logic (skip already-bridged products)
- Keep `--rebuild` flag (wipes ALL bridges, not just pass-1 bridges)

### `compute_bridges_v2.py` structure

```python
"""
Bridge discovery passes 2-4: Opposition, Shared Purpose, Parallel Form.

Runs AFTER compute_bridges.py. Additive — uses ON CONFLICT DO NOTHING.
Each pass uses a different candidate selection strategy (no vector search).

Usage:
  python analysis/compute_bridges_v2.py                          # all passes
  python analysis/compute_bridges_v2.py --pass=opposition        # single pass
  python analysis/compute_bridges_v2.py --pass=function          # single pass
  python analysis/compute_bridges_v2.py --pass=structural        # single pass
  python analysis/compute_bridges_v2.py --dry-run                # report only
  python analysis/compute_bridges_v2.py --dry-run --pass=opposition
"""

def build_vibe_index(products) -> dict[str, set[int]]
def build_function_index(products) -> dict[str, set[int]]
def build_structural_groups(products) -> dict[tuple[str,str], set[int]]

def run_opposition_pass(db, product_map, embedding_cache, vibe_index, existing_pairs, ...) -> int
def run_function_pass(db, product_map, embedding_cache, function_index, existing_pairs, ...) -> int
def run_structural_pass(db, product_map, embedding_cache, structural_groups, existing_pairs, ...) -> int

def main():
    db = SessionLocal()
    products = load_eligible_products(db)   # shared with compute_bridges.py
    product_map = {p.id: p for p in products}
    existing_pairs = load_existing_pairs(db)
    embedding_cache = {}                     # lazy-loaded, {product_id: (text_vec, image_vec)}

    # Run selected passes
    # Print per-pass summaries
    db.close()
```

### Embedding cache

Passes 2-4 don't use vector search for candidates, but they still need text/image similarity for the composite bridge score. Rather than querying embeddings per-pair, use a lazy cache:

```python
def get_embeddings(db, product_id, cache):
    """Lazy-load and cache embeddings for a product."""
    if product_id not in cache:
        row = db.execute(
            text("SELECT text_embedding, image_embedding FROM products WHERE id = :id"),
            {"id": product_id}
        ).fetchone()
        cache[product_id] = (row[0], row[1]) if row else (None, None)
    return cache[product_id]
```

---

## Execution

### Full rebuild (clean slate)

```bash
# 1. Wipe and recompute vector-based bridges
venv/bin/python analysis/compute_bridges.py --rebuild

# 2. Add opposition, function, structural bridges
venv/bin/python analysis/compute_bridges_v2.py

# 3. Classify all bridges (6 dimensions)
venv/bin/python scripts/classify_bridge_dimensions.py

# 4. Generate narratives (mode-specific prompts)
venv/bin/python analysis/generate_narratives.py
```

### Incremental (add V2 passes to existing bridges)

```bash
# Just add the new passes — ON CONFLICT DO NOTHING protects existing bridges
venv/bin/python analysis/compute_bridges_v2.py

# Re-classify (new bridges need classification)
venv/bin/python scripts/classify_bridge_dimensions.py

# Generate narratives for new bridges only
venv/bin/python analysis/generate_narratives.py
```

### Dry run (see what would be found)

```bash
venv/bin/python analysis/compute_bridges_v2.py --dry-run
# Output: candidate counts, score distributions, sample bridges per pass
```

---

## Expected Yield

| Pass | Strategy | Expected bridges | Connection modes found |
|------|----------|-----------------|----------------------|
| 1. Similarity | Vector proximity | ~5,000-8,000 | Affinity, resonance |
| 2. Opposition | Vibe cross-join | ~50-200 | Contrast (by design) |
| 3. Shared Purpose | Function grouping | ~100-300 | Mixed (cross-cultural affinity, contrast) |
| 4. Parallel Form | Structural grouping | ~50-150 | Affinity (with "independent invention" flavor) |

**Total:** ~5,500-8,700 bridges with much better diversity across connection modes.

**Quality improvement:** V1 produces almost exclusively affinity bridges because vector proximity selects for similarity. V2 adds targeted discovery for contrast (Pass 2), comparison (Pass 3), and parallel invention (Pass 4) — bridge types that vector search structurally cannot find.

---

## Thresholds to Tune

| Parameter | Pass | Starting value | Adjust if... |
|-----------|------|---------------|--------------|
| top_k (vector candidates) | 1 | 30 | Too few affinity bridges → 50. Too slow → 20 |
| structural_gate | 2 | 0.3 | <3% of candidates pass → 0.2. >15% → 0.4 |
| top_per_pair | 2 | 20 | Some pairs produce <20 → OK, just take what exists |
| top_per_function | 3 | 15 | Dominant functions (ceremony) drown others → lower to 10 |
| boundary requirement | 3 | cross ≥1 of culture/era/category | Too strict → drop category |
| min_structural | 4 | 0.40 | Too few structural matches → 0.30 |
| discovery_bonus | 4 | +0.10 at text_sim < 0.4 | Most pairs get bonus → raise threshold to 0.3 |

---

## Open Questions

1. **Should opposition bridges skip the text/image sim entirely?** The structural gate + vibe opposition might be sufficient. Text/image sim adds compute cost and the signal is weak for contrast bridges (by definition, opposing items don't describe similarly). Counter-argument: even a small text_sim component helps rank — two structurally similar opposing pairs can be distinguished by which one has slightly more semantic overlap.

2. **Should function pass prefer LOW structural scores?** The most interesting "same question, different answer" bridges might be pairs with shared function but *zero* structural overlap — completely different solutions to the same problem. These would rank low on bridge_score. Maybe function bridges need a separate scoring formula that doesn't penalize structural divergence.

3. **How to handle the "discovery" tag in shared_attributes?** If a pair is found by both Pass 1 (vector) and Pass 2 (opposition), ON CONFLICT DO NOTHING means Pass 1's metadata wins (it runs first). Should we instead use ON CONFLICT DO UPDATE to merge? Or just accept first-writer-wins?

4. **Should we run passes 2-4 before pass 1?** If contrast and function bridges are the most interesting, maybe they should get first-writer advantage on metadata. Pass 1 would then fill in the affinity/resonance bridges that the targeted passes didn't find.

5. **Products with multiple core_vibes:** A product with `["Exaggerated Volume", "Maximalist Ornament"]` participates in multiple opposition pairs. This is fine — the same product can appear in multiple bridges. But it means some products will be disproportionately represented in contrast bridges. Cap at N bridges per product per pass if this becomes an issue.
