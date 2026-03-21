# Compute Bridges — Reference Document

> `tools/analysis/better_bridges.py`
>
> Entity-based bridge discovery. Finds connections between garments through
> shared designers, movements, techniques, influence citations, and visual similarity.
> Every bridge has a typed reason stored in `shared_entities`.

## Usage

```bash
# Full rebuild (deletes all existing bridges)
PYTHONPATH=. python tools/analysis/better_bridges.py --rebuild

# Dry run — calculate everything, write nothing to DB
PYTHONPATH=. python tools/analysis/better_bridges.py --dry-run --limit=100

# Skip visual echo pass (faster iteration)
PYTHONPATH=. python tools/analysis/better_bridges.py --rebuild --skip-visual

# Limit to N products (for testing)
PYTHONPATH=. python tools/analysis/better_bridges.py --rebuild --limit=50
```

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     LOAD & PREPARE                                  │
│  Products → parse entities → build inverted index → compute IDF    │
│  Load text + image embeddings into memory                           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ┌───────────┐    ┌───────────┐    ┌───────────┐
   │  PASS 1   │    │  PASS 2   │    │  PASS 3   │
   │  Shared   │    │  Lineage  │    │  Visual   │
   │  Entities │    │ (directed)│    │  Echo     │
   │           │    │           │    │           │
   │ inverted  │    │ influence │    │ pgvector  │
   │ index     │    │ reference │    │ image kNN │
   │ cross-join│    │ matching  │    │           │
   └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
         │                │                │
         │  save to DB    │  save to DB    │  batch save
         ▼                ▼                ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                    SUMMARY & STATS                           │
   │  Total bridges, by pass, by crossing, score distribution    │
   │  Top shared entities                                         │
   └─────────────────────────────────────────────────────────────┘
```

Saves after each pass — resilient to crashes and Supabase pooler timeouts.

---

## The Three Passes

### Pass 1: Shared Entities

**Strategy:** Inverted index lookup. For each entity value (e.g., "Japonisme", "Perry Ellis"), find all products sharing it, cross-join into candidate pairs, score by IDF-weighted entity overlap.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Candidate source | Inverted index cross-join | No embedding queries needed |
| MAX_PAIRS_PER_ENTITY | 200 | Skip entity values shared by >200 products (noise) |
| MIN_ENTITY_SCORE | 5.0 | Minimum IDF-weighted entity overlap |
| SAME_ERA_MIN_ENTITY_SCORE | 8.0 | Stricter gate when both products share an era |
| MIN_ENTITY_IDF | 2.0 | At least one shared entity must have IDF ≥ 2.0 |
| SAME_ERA_MAX_BRIDGES | 300 | Per-era cap for same-era bridges |
| Boundary rule | `_crosses_boundary()` | 30+ yr gap OR different culture |
| Participation cap | 15 per product | |
| connection_mode | `shared_entity` | Always |
| directed | `False` | Always |

**Entity Scoring:**

Each shared entity value contributes: `IDF(value) × type_multiplier`

IDF = `log(total_products / count_with_value)` — rare entities score higher.

| Entity Type | Multiplier | Example |
|-------------|-----------|---------|
| designer | 3.0 | "Perry Ellis" (IDF ~7.1) → 21.3 points |
| influence_references | 2.5 | "1890s leg-of-mutton sleeve" |
| named_movements | 2.0 | "Japonisme" (IDF ~5.6) → 11.2 points |
| garment_system | 1.5 | "corset" + "chemise" |
| construction_technique | 1.0 | "hand-embroidery" |
| social_function | 1.0 | "military-uniform" |
| motif_family | 0.75 | "paisley" |

**Demoted multiplier:** `construction_technique` and `garment_system` values with IDF < 2.0 get 0.25× multiplier instead of full. Common terms like "hand-sewing" contribute almost nothing.

**Entity Blocklist:** These values are excluded from `shared_entities` display (still scored):
- social_function: `everyday-practical`, `status-signaling`
- construction_technique: `hand-sewing`, `machine-sewing`, `tailoring`
- motif_family: `none`, `geometric`, `floral`

A bridge needs at least one non-blocklisted entity with IDF ≥ 2.0 to qualify.

**Filters applied (in order):**
1. Already in `existing_pairs` → skip
2. `_crosses_boundary()` → must cross time or culture
3. Same-era cap check → per-era limit
4. Entity score < threshold → skip
5. Has no rare entity → skip
6. `_too_similar()` → reject near-duplicates
7. Participation cap → skip if either product has 15 bridges

---

### Pass 2: Lineage (Directed)

**Strategy:** Match `influence_references` against the product corpus. For each product with influences, find the best-matching product that IS what's being referenced.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Candidate source | Word index + era pre-filter | Fast lookup, no N² scan |
| Matching | Word overlap + era bonus + movement bonus | Scores 0-1.6 |
| Embedding fallback | Text similarity for unmatched influences | Sorted by word overlap, cap 300 |
| Min match score | 0.4 | Minimum quality for a match |
| LINEAGE_BONUS | 5.0 | Added to entity_score — the reference itself is a high-value entity |
| Direction | source = older (original), target = newer (referencer) | Always older → newer |
| Participation cap | 15 per product | |
| connection_mode | `lineage` | Always |
| directed | `True` | Always |

**Era parsing:** Extracts decade ("1890s"), century ("18th century"), and era keywords ("Victorian", "Art Deco", etc.) from influence reference strings. Pre-filters candidates to the right era before word matching.

**One best match per influence reference** — prevents "1890s bustle" from generating 12 bridges.

**Lineage bridges may NOT use canonical ordering** — source_id can be > target_id when the older item has a higher database ID.

---

### Pass 3: Visual Echo

**Strategy:** pgvector image similarity search for pairs NOT already connected by Passes 1-2. Finds "surprises that metadata missed."

| Parameter | Value | Notes |
|-----------|-------|-------|
| Candidate source | pgvector kNN | `image_embedding <=>` |
| top_k | 10 | Image candidates per product |
| VISUAL_ECHO_MIN_IMAGE_SIM | 0.80 | Minimum image similarity |
| Boundary rule | `_crosses_boundary()` | 30+ yr gap OR different culture |
| Participation cap | 15 per product | |
| connection_mode | `visual_echo` | Always |
| directed | `False` | Always |
| Batch commits | Every 500 bridges | Survives pooler timeouts |

**Key constraint:** `if pair_key in existing_pairs: continue` — only finds connections that entity matching and lineage missed.

---

## Scoring

### Bridge Score

```
raw = entity_score + context_score + embedding_bonus + surprise_bonus

bridge_score = 1 - (1 / (1 + raw / 10))   # sigmoid normalization to 0-1
```

**Mapping:** raw 10 → ~0.50, raw 20 → ~0.67, raw 40 → ~0.80

### Context Score

```
context_score = year_gap_bonus + crossing_bonus

year_gap_bonus = min(year_gap / 10, 10) × 0.05 × precision_factor
  precision_factor: decade+decade = 1.0, decade+era = 0.7, era+era = 0.4

crossing_bonus:
  cross_culture = 0.4
  cross_category_culture = 0.35
  cross_category = 0.05
  same_context = 0
```

### Embedding Bonus

Small confirmation boost — not a primary signal:
```
text_sim × 0.1    (max +0.1)
image_sim × 0.1   (max +0.1)
```

### Surprise Bonus

Rewards "hidden connections" — high entity overlap + low visual similarity:
```
if entity_score >= 8.0 AND image_sim < 0.4:
    surprise_bonus = (1.0 - image_sim) × 0.3    # max +0.3
```

---

## Near-Duplicate Detection

`_too_similar(prod_a, prod_b, text_sim, image_sim)` — rejects pairs that are basically the same item.

| Check | Condition | Catches |
|-------|-----------|---------|
| Same-era text ceiling | same era + text_sim ≥ 0.90 | Two Victorian dresses with near-identical descriptions |
| High image + moderate text | image_sim ≥ 0.93 + text_sim ≥ 0.65 | Visually identical items |
| Combined average | (text_sim + image_sim) / 2 ≥ 0.87 | Generally too similar |

---

## Boundary Crossing

`_crosses_boundary(prod_a, prod_b)` — both cultures must be non-empty for culture crossing.

```
Different culture (both non-null)?  ──YES──→ ✓ crosses
        │ NO
        ▼
Year gap ≥ 30?                      ──YES──→ ✓ crosses
        │ NO / unknown
        ▼
        ✗ does not cross (pair dropped)
```

---

## Database Schema (StyleBridge)

| Column | Type | Source |
|--------|------|--------|
| id | Integer (PK) | Auto |
| source_id | Integer (FK → products) | Canonical or directed |
| target_id | Integer (FK → products) | Canonical or directed |
| bridge_score | Float | Precomputed composite (0-1) |
| entity_score | Float | IDF-weighted entity overlap |
| text_similarity | Float (nullable) | Cosine sim of text embeddings |
| image_similarity | Float (nullable) | Cosine sim of image embeddings |
| connection_mode | String | `shared_entity`, `lineage`, `visual_echo` |
| crossing_type | String | `same_context`, `cross_category`, `cross_culture`, `cross_category_culture` |
| year_gap | Integer (nullable) | Actual year distance |
| directed | Boolean | True for lineage (source=older, target=newer) |
| shared_entities | Text (JSON) | `{entity_type: [values]}` — the "why" |
| bridge_narrative | Text (nullable) | AI-generated, populated by `generate_narratives.py` |
| created_at | DateTime | |

Unique constraint: `uq_bridge_pair` on `(source_id, target_id)`.

### shared_entities JSON

```json
{
  "designer": ["Perry Ellis"],
  "named_movements": ["Power Dressing"],
  "construction_technique": ["couture-construction"],
  "lineage_reference": "1940s double-breasted silhouette",
  "lineage_match_score": 0.85
}
```

Blocklisted values (everyday-practical, hand-sewing, etc.) are excluded from display but still contribute to entity_score.

---

## Downstream Pipeline

```
better_bridges.py
        │
        ▼
generate_narratives.py ─── Claude generates 2-3 sentence editorial
        │                   narratives with product images
        │                   One adaptive prompt for all bridge types
        │                   Quality gate: bridge_score ≥ 0.55
        │                   (lineage/visual_echo: ≥ 0.45)
        ▼
bridge_queries.py ──────── Query functions for API
        │                   Sorted by bridge_score DESC
        │                   Randomized sampling from top pool
        ▼
api/routers/bridges.py ─── REST API: /bridges/top, /bridges/{id},
                            /bridges/between/{a}/{b}, /bridges/stats
                            /products/{id}/bridges
```

---

## Constants Reference

| Constant | Value | Used by |
|----------|-------|---------|
| `MIN_ENTITY_SCORE` | 5.0 | Pass 1 gate |
| `SAME_ERA_MIN_ENTITY_SCORE` | 8.0 | Pass 1 same-era gate |
| `MIN_ENTITY_IDF` | 2.0 | Rarity requirement |
| `MAX_PAIRS_PER_ENTITY` | 200 | Pass 1 explosion cap |
| `MAX_BRIDGES_PER_PRODUCT` | 15 | All passes |
| `SAME_ERA_MAX_BRIDGES` | 300 | Per-era cap |
| `BOUNDARY_YEAR_GAP` | 30 years | Passes 1, 3 |
| `VISUAL_ECHO_MIN_IMAGE_SIM` | 0.80 | Pass 3 |
| `LINEAGE_BONUS` | 5.0 | Pass 2 entity score boost |
| `LINEAGE_MIN_TEXT_SIM` | 0.40 | Pass 2 embedding fallback |
| `TOO_SIMILAR_TEXT` | 0.90 | Same-era text ceiling |
| `TOO_SIMILAR_IMAGE` | 0.93 | Image similarity ceiling |
| `TOO_SIMILAR_COMBINED` | 0.87 | Combined average ceiling |

### Entity Type Multipliers

| Type | Multiplier | Demoted (IDF < 2.0) |
|------|-----------|---------------------|
| designer | 3.0 | — |
| influence_references | 2.5 | — |
| named_movements | 2.0 | — |
| garment_system | 1.5 | 0.25 |
| construction_technique | 1.0 | 0.25 |
| social_function | 1.0 | — |
| motif_family | 0.75 | — |

### Context Weights

| Crossing | Bonus |
|----------|-------|
| cross_culture | 0.4 |
| cross_category_culture | 0.35 |
| cross_category | 0.05 |
| year_gap_per_decade | 0.05 (caps at 10 decades) |
