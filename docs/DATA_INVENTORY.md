# Vintage Vestige — Data Inventory

**As of: 2026-02-22 (all numbers from live queries)**

---

## PostgreSQL Database

### Connection

```
DATABASE_URL=postgresql+psycopg://localhost/vintage_vestige
```

### Tables

```sql
-- Query: SELECT tablename FROM pg_tables WHERE schemaname = 'public'
-- Result:
  products
  style_bridges
```

No other tables exist. The IIT 4.0 plan calls for `phi_scores`, `maximal_complexes`, and `discovered_complexes` — none of these have been created.

---

### Products Table: 866 rows

#### By Platform

```sql
-- Query: SELECT platform, COUNT(*) FROM products GROUP BY platform
-- Result:
  fashionpedia:  500
  met_museum:    200
  smithsonian:   166
  ─────────────────
  Total:         866
```

#### Enrichment Coverage

```sql
-- Query: SELECT COUNT(*) FROM products WHERE enriched_at IS NOT NULL
-- Result: 866/866 (100%)
```

All products have been enriched by Claude Sonnet 4.

#### Embedding Timestamp Coverage

```sql
-- Query: SELECT COUNT(*) FROM products WHERE embedded_at IS NOT NULL
-- Result: 200/866 (23%)
```

**Important caveat:** All 866 products ARE in Qdrant (confirmed below). The `embedded_at` timestamp was only set for the first 200 products (Met Museum batch). The remaining 666 were embedded via `rebuild_embeddings.py` or `enrich_and_reembed_all.py` which didn't update this timestamp. This is a tracking gap, not a data gap.

#### Field Coverage (non-null, non-empty counts out of 866)

| Field | Count | Coverage | Notes |
|-------|-------|----------|-------|
| **title** | 866 | 100% | |
| **description** | 866 | 100% | |
| **primary_image** | 866 | 100% | URLs or data URLs |
| **price** | 866 | 100% | Set to 0.0 for museum items |
| **url** | 866 | 100% | |
| **seller_name** | 866 | 100% | Museum name for museum items |
| **image_urls** | 866 | 100% | JSON array |
| **era** | 866 | 100% | From enrichment |
| **decade** | 865 | 99.9% | 1 item missing |
| **category** | 866 | 100% | |
| **vibe** | 866 | 100% | From enrichment |
| **fit_style** | 866 | 100% | From enrichment |
| **occasion** | 866 | 100% | From enrichment |
| **ai_description** | 866 | 100% | From enrichment |
| **enriched_text** | 866 | 100% | Built from enrichment fields |
| **colors** | 866 | 100% | JSON array, from enrichment |
| **material** | 866 | 100% | From enrichment |
| **style_tags** | 866 | 100% | JSON array, from enrichment |
| **garment_type** | 866 | 100% | From enrichment |
| **textile_finishing** | 866 | 100% | JSON array, from enrichment |
| **garment_parts** | 866 | 100% | JSON array, from enrichment |
| **decorations** | 866 | 100% | JSON array, from enrichment |
| **fp_category** | 855 | 98.7% | 11 items missing |
| **textile_pattern** | 845 | 97.6% | 21 items missing |
| **silhouette** | 753 | 86.9% | Accessories lack silhouette |
| **waistline** | 697 | 80.5% | Not applicable to all garments |
| **length** | 656 | 75.8% | Not applicable to all garments |
| **nickname** | 508 | 58.7% | Many items have no specific sub-type |
| **culture** | 344 | 39.7% | Museum items have culture; Fashionpedia doesn't |
| **sleeve_length** | 211 | 24.4% | Many garments are sleeveless/N/A |
| **object_date** | 158 | 18.2% | Smithsonian items have dates |
| **neckline** | 135 | 15.6% | Many garments lack visible neckline |
| **color** | 0 | 0% | Original dataset field; superseded by `colors` |
| **season** | 0 | 0% | Original dataset field; enrichment uses `season` from enrichment |
| **year** | 0 | 0% | Original dataset field; superseded by `decade` |
| **pattern** | 0 | 0% | Original dataset field; superseded by `textile_pattern` |
| **period** | 0 | 0% | Never populated |

**Key observation:** Several original dataset fields (`color`, `season`, `year`, `pattern`, `period`) are completely empty — enrichment fields (`colors`, `season` via enrichment, `decade`, `textile_pattern`) have replaced them. These columns are dead weight.

---

### Style Bridges Table: 7,324 rows

#### By Bridge Type

```sql
-- Query: SELECT bridge_type, COUNT(*) FROM style_bridges GROUP BY bridge_type
-- Result:
  same_era:         3,957  (54.0%)
  cross_category:   1,760  (24.0%)
  cross_era:        1,076  (14.7%)
  near_era:           425  ( 5.8%)
  cross_vibe:         106  ( 1.4%)
  ──────────────────────────────────
  Total:            7,324
```

#### Score Distribution

```sql
-- Query: Score histogram (0.1 buckets)
-- Result:
  0.0-0.1:     0
  0.1-0.2:     0
  0.2-0.3:     0
  0.3-0.4:   623   ( 8.5%)
  0.4-0.5: 1,841   (25.1%)
  0.5-0.6: 2,182   (29.8%)  ← peak
  0.6-0.7: 1,838   (25.1%)
  0.7-0.8:   728   ( 9.9%)
  0.8-0.9:   108   ( 1.5%)
  0.9-1.0:     4   ( 0.1%)

  AVG: 0.5560   MIN: 0.3000   MAX: 0.9348
```

#### Image Similarity Coverage

```sql
-- Query: SELECT COUNT(*) FROM style_bridges WHERE image_similarity IS NOT NULL
-- Result: 2,243/7,324 (30.6%)
```

69.4% of bridges lack image similarity — these use the fallback scoring formula (0.55*text + 0.45*structural).

#### Narrative Coverage

```sql
-- Query: SELECT COUNT(*) FROM style_bridges WHERE bridge_narrative IS NOT NULL
-- Result: 22/7,324 (0.3%)
```

Only 22 narratives generated out of 7,324 bridges. The async generation script ([analysis/generate_narratives.py](../analysis/generate_narratives.py)) is ready to run the remaining ~7,302.

**Estimated cost to complete:** ~$13 at current Claude Sonnet 4 pricing (7,302 calls × ~200 tokens each).

#### Cross-Platform Bridges

```sql
-- Query: SELECT COUNT(*) FROM style_bridges sb
--   JOIN products p1 ON sb.source_id = p1.id
--   JOIN products p2 ON sb.target_id = p2.id
--   WHERE p1.platform != p2.platform
-- Result: 1,134/7,324 (15.5%)
```

#### Sample Bridge

```sql
-- Query: SELECT * FROM style_bridges WHERE bridge_narrative IS NOT NULL LIMIT 1
-- Result:
  source_id: 209, target_id: 221
  bridge_score: 0.9348, bridge_type: same_era
  text_similarity: 0.9551, image_similarity: NULL, structural_score: 0.91
  narrative: "Both items embody the Georgian era's revolutionary shift toward
    neoclassical simplicity, featuring the distinctive empire waistline that
    sits just below the bust and flows into an A-line silhouette ma..."
```

---

## Qdrant Vector Database

### Connection

```
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### Collection: `vintage_text`

```python
# Query: client.get_collection('vintage_text')
# Result:
  points_count: 866
  vector_size:  384
  distance:     Cosine
```

**Payload fields (21):** product_id, title, category, era, decade, style_tags, colors, material, pattern, garment_type, vibe, fit_style, occasion, ai_description, season, price, primary_image, culture, object_date, platform, fp_category

**Platform distribution:**

```python
# Query: client.count(filter=FieldCondition(key='platform', match=MatchValue(value=X)))
# Result:
  fashionpedia: 500
  met_museum:   200
  smithsonian:  166
  Total:        866
```

All 866 points have `platform` and `fp_category` in their payloads (confirmed by filter queries and sampling).

### Collection: `vintage_images`

```python
# Query: client.get_collection('vintage_images')
# Result:
  points_count: 866
  vector_size:  512
  distance:     Cosine
```

**Payload fields (28, backfilled 2026-02-22):** product_id, platform, title, category, era, decade, style_tags, colors, material, garment_type, vibe, fit_style, occasion, ai_description, price, primary_image, culture, object_date, fp_category, nickname, silhouette, neckline, waistline, length, sleeve_length, opening_type, textile_pattern, textile_finishing, garment_parts, decorations

**Platform distribution:**

```python
# Query: (same as above)
# Result:
  fashionpedia: 500
  met_museum:   200
  smithsonian:  166
  Total:        866
```

**Note:** Payloads were backfilled on 2026-02-22 using `embeddings/scripts/backfill_image_payloads.py` (Qdrant `set_payload()` — vectors untouched). Both collections now have identical payload shapes. The `generate_image_embeddings.py` script was also updated to include full payloads for future runs.

---

## Data Quality Notes

1. **`embedded_at` tracking gap:** Only 200/866 products have this timestamp set, despite all 866 being in Qdrant. Safe to backfill with a one-liner: `UPDATE products SET embedded_at = NOW() WHERE embedded_at IS NULL`.

2. **Dead columns:** `color`, `season`, `year`, `pattern`, `period` are all 0/866 populated. The enrichment fields (`colors`, `decade`, `textile_pattern`) have replaced them. These columns should be dropped or ignored.

3. **Image payload asymmetry: RESOLVED.** `vintage_images` payloads were backfilled on 2026-02-22 to match `vintage_text` (28 fields each). No Postgres join needed for image search.

4. **Narrative gap:** 22/7,324 bridges have narratives. Running `generate_narratives.py` would cost ~$13 and take ~1 hour (7,302 bridges × ~0.5s each with concurrency 10).

5. **Neckline/sleeve_length sparsity:** Only 15.6% and 24.4% populated respectively. These contribute to structural scoring but are often NULL for non-applicable garment types (accessories, bags, hats). The scoring algorithm handles NULL correctly (field is simply ignored).
