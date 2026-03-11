# Vintage Vestige — Data Inventory

**As of: 2026-03-09**

---

## Supabase PostgreSQL Database (with pgvector)

### Connection

```
DATABASE_URL=postgresql+psycopg://postgres:***@db.tusswxlrdoamintvswjs.supabase.co:5432/postgres
```

### Tables

```sql
-- Query: SELECT tablename FROM pg_tables WHERE schemaname = 'public'
-- Result:
  products
  style_bridges
```

No other tables exist. The IIT 4.0 plan calls for `phi_scores`, `maximal_complexes`, and `discovered_complexes` — none of these have been created. The products table now includes pgvector columns `text_embedding vector(384)` and `image_embedding vector(512)` with HNSW indexes.

---

### Products Table: 4,234 rows

#### By Platform

```sql
-- Query: SELECT platform, COUNT(*) FROM products GROUP BY platform ORDER BY COUNT(*) DESC
-- Result:
  va_museum:     1,856
  fashionpedia:  1,000
  smithsonian:     778
  met_museum:      600
  ─────────────────────
  Total:         4,234
```

#### Enrichment Coverage

```sql
-- Query: SELECT COUNT(*) FROM products WHERE enriched_at IS NOT NULL
-- Result: 4,234/4,234 (100%)
```

All products enriched via `enrich_async.py` (concurrency 10-15). All products have `core_vibes` (vibe vocabulary from updated enrichment prompts).

#### Embedding Coverage

```sql
-- Query: SELECT COUNT(*) FROM products WHERE text_embedding IS NOT NULL
-- Result: 4,234/4,234 (100%)

-- Query: SELECT COUNT(*) FROM products WHERE image_embedding IS NOT NULL
-- Result: 4,234/4,234 (100%)
```

All products re-embedded using `enriched_text` via `rebuild_embeddings.py` (2026-03-06).

#### Field Coverage (non-null, non-empty counts out of 4,234)

| Field | Count | Coverage | Notes |
|-------|-------|----------|-------|
| **title** | 4,234 | 100% | |
| **description** | 4,234 | 100% | |
| **primary_image** | 4,234 | 100% | All HTTP URLs (Supabase Storage) |
| **price** | 4,234 | 100% | Set to 0.0 for museum items |
| **url** | 4,234 | 100% | |
| **seller_name** | 4,234 | 100% | Museum name for museum items |
| **image_urls** | 4,234 | 100% | JSON array |
| **era** | 4,234 | 100% | From enrichment |
| **decade** | ~4,230 | ~99.9% | A few items missing |
| **category** | 4,234 | 100% | |
| **vibe** | 4,234 | 100% | From enrichment |
| **core_vibes** | 4,234 | 100% | JSON array, controlled vocabulary |
| **fit_style** | 4,234 | 100% | From enrichment |
| **occasion** | 4,234 | 100% | From enrichment |
| **ai_description** | 4,234 | 100% | From enrichment |
| **enriched_text** | 4,234 | 100% | Built from enrichment fields |
| **colors** | 4,234 | 100% | JSON array, from enrichment |
| **material** | 4,234 | 100% | From enrichment |
| **style_tags** | 4,234 | 100% | JSON array, from enrichment |
| **garment_type** | 4,234 | 100% | From enrichment |
| **textile_finishing** | 4,234 | 100% | JSON array, from enrichment |
| **garment_parts** | 4,234 | 100% | JSON array, from enrichment |
| **decorations** | 4,234 | 100% | JSON array, from enrichment |
| **social_function** | 4,234 | 100% | JSON array, from enrichment |
| **construction_technique** | 4,234 | 100% | JSON array, from enrichment |
| **motif_family** | 4,234 | 100% | JSON array, from enrichment |
| **fp_category** | ~98% | ~98% | Some items not classifiable |
| **textile_pattern** | ~97% | ~97% | Some items missing |
| **silhouette** | ~85% | ~85% | Accessories lack silhouette |
| **waistline** | ~80% | ~80% | Not applicable to all garments |
| **length** | ~75% | ~75% | Not applicable to all garments |
| **nickname** | ~58% | ~58% | Many items have no specific sub-type |
| **culture** | ~75% | ~75% | Museum items have culture; Fashionpedia enriched by Claude |
| **sleeve_length** | ~25% | ~25% | Many garments are sleeveless/N/A |
| **object_date** | ~18% | ~18% | Smithsonian items have dates |
| **neckline** | ~16% | ~16% | Many garments lack visible neckline |
| **color** | 0 | 0% | Dead column; superseded by `colors` |
| **season** | 0 | 0% | Dead column; superseded by enrichment |
| **year** | 0 | 0% | Dead column; superseded by `decade` |
| **pattern** | 0 | 0% | Dead column; superseded by `textile_pattern` |
| **period** | 0 | 0% | Never populated |

**Key observation:** Several original dataset fields (`color`, `season`, `year`, `pattern`, `period`) are completely empty — enrichment fields have replaced them. These columns are dead weight.

---

### Style Bridges Table: Being Recomputed

Bridge recomputation (`compute_bridges.py --rebuild`) started 2026-03-07 over all 4,234 enriched/embedded products. Previous 3,367 bridges were wiped for rebuild.

#### Bridge Types (from computation passes)

- **Pass 1 (Open discovery):** text + image similarity across all products
- **Pass 2 (Cross-culture):** bridges between products with different cultures

#### Classification Columns (NEW 2026-03-07)

6 orthogonal dimensions added to `style_bridges`:

| Column | Values |
|--------|--------|
| `temporal_type` | transmission \| continuation \| contemporary |
| `crossing_type` | same_context \| cross_category \| cross_culture \| cross_category_culture |
| `connection_mode` | contrast \| resonance \| affinity |
| `primary_axis` | volume \| ornament \| body \| register |
| `secondary_axis` | volume \| ornament \| body \| register |
| `contrast_pair` | e.g. "Exaggerated Volume <-> Column Minimalism" (contrast only) |

Classification runs post-hoc via `tools/analysis/classify_bridge_dimensions.py`.

#### Narrative Coverage

Narratives will be regenerated after bridge recomputation via `tools/analysis/generate_narratives.py`. New narratives receive full classification context:
- Mode-specific system prompts (contrast: explain tension in 2 sentences / 60 words; resonance/affinity: 1 sentence / 40 words)
- Varied closing instructions based on temporal_type, crossing_type, connection_mode
- Vibe data (core_vibes for both items)
- Formatted shared attributes (readable text, not raw JSON)

---

## Vector Embeddings (pgvector — on products table)

**Migrated from Qdrant 2026-03-04.** Local Qdrant is stopped and removed from `.env`.

### Text Embeddings

```sql
-- Query: SELECT COUNT(*) FROM products WHERE text_embedding IS NOT NULL
-- Result: 4,234/4,234 (100%)
-- Dimensionality: 384 (all-MiniLM-L6-v2)
-- Index: HNSW with vector_cosine_ops
```

### Image Embeddings

```sql
-- Query: SELECT COUNT(*) FROM products WHERE image_embedding IS NOT NULL
-- Result: 4,234/4,234 (100%)
-- Dimensionality: 512 (clip-ViT-B-32)
-- Index: HNSW with vector_cosine_ops
```

All products embedded using `enriched_text` (text) and product images (CLIP). Re-embedded 2026-03-06 via `rebuild_embeddings.py`.

## Supabase Storage

### Bucket: `product-images`

```
URL pattern: https://tusswxlrdoamintvswjs.supabase.co/storage/v1/object/public/product-images/{id}.{ext}
Total files: 4,234 (one per product)
Format: JPEG (.jpg)
Access: Public bucket (no auth required)
```

**Migrated 2026-03-04** from base64 `data:image/jpeg;base64,...` strings in the `primary_image` column. All products now reference Supabase Storage URLs.

---

## Data Quality Notes

1. **`embedded_at` tracking gap:** Not all products have this timestamp set despite having embeddings. Low priority — embeddings themselves are complete.

2. **Dead columns:** `color`, `season`, `year`, `pattern`, `period` are all 0% populated. The enrichment fields (`colors`, `decade`, `textile_pattern`) have replaced them.

3. **Neckline/sleeve_length sparsity:** ~16% and ~25% populated respectively. These contribute to structural scoring but are often NULL for non-applicable garment types. The scoring algorithm handles NULL correctly.

4. **Bridge recomputation in progress:** `compute_bridges.py --rebuild` running 2026-03-07 over full 4,234-product corpus. After completion: classify dimensions, then generate narratives.
